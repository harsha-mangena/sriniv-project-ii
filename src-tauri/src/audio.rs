//! Audio capture module for system audio (ScreenCaptureKit) and microphone (cpal).
//!
//! Captures audio from two sources:
//! 1. System audio via ScreenCaptureKit (macOS 12.3+) — captures meeting/interviewer audio
//! 2. Microphone via cpal — captures user's voice
//!
//! Both streams are chunked into 5-second windows with 1-second overlap and sent
//! to the transcription pipeline.

use log::{error, info, warn};
use parking_lot::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Sample rate optimized for speech recognition.
pub const SAMPLE_RATE: u32 = 16_000;

/// Chunk duration in seconds.
const CHUNK_DURATION_SECS: f64 = 5.0;

/// Overlap between consecutive chunks in seconds.
const CHUNK_OVERLAP_SECS: f64 = 1.0;

/// Samples per chunk.
const CHUNK_SAMPLES: usize = (SAMPLE_RATE as f64 * CHUNK_DURATION_SECS) as usize;

/// Overlap samples.
const OVERLAP_SAMPLES: usize = (SAMPLE_RATE as f64 * CHUNK_OVERLAP_SECS) as usize;

/// Identifies the audio source for speaker labeling.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AudioSource {
    /// System audio (interviewer/meeting participants)
    System,
    /// Microphone (the user)
    Microphone,
}

/// An audio chunk ready for transcription.
#[derive(Debug, Clone)]
pub struct AudioChunk {
    pub samples: Vec<f32>,
    pub source: AudioSource,
    pub timestamp_ms: i64,
}

/// Manages audio capture from system and microphone sources.
pub struct AudioCapture {
    is_recording: Arc<AtomicBool>,
    system_buffer: Arc<Mutex<Vec<f32>>>,
    mic_buffer: Arc<Mutex<Vec<f32>>>,
    chunk_sender: tokio::sync::mpsc::Sender<AudioChunk>,
}

impl AudioCapture {
    pub fn new(chunk_sender: tokio::sync::mpsc::Sender<AudioChunk>) -> Self {
        Self {
            is_recording: Arc::new(AtomicBool::new(false)),
            system_buffer: Arc::new(Mutex::new(Vec::with_capacity(CHUNK_SAMPLES * 2))),
            mic_buffer: Arc::new(Mutex::new(Vec::with_capacity(CHUNK_SAMPLES * 2))),
            chunk_sender,
        }
    }

    /// Start capturing audio from both system and microphone.
    pub fn start(&self) -> Result<(), String> {
        if self.is_recording.load(Ordering::SeqCst) {
            return Err("Already recording".to_string());
        }

        self.is_recording.store(true, Ordering::SeqCst);
        info!("Starting audio capture...");

        // Start microphone capture
        self.start_microphone()?;

        // Start system audio capture (macOS only)
        #[cfg(target_os = "macos")]
        self.start_system_audio()?;

        #[cfg(not(target_os = "macos"))]
        warn!("System audio capture only available on macOS");

        // Start chunk extraction loop for both sources
        self.start_chunking_loop(AudioSource::Microphone, self.mic_buffer.clone());
        self.start_chunking_loop(AudioSource::System, self.system_buffer.clone());

        info!("Audio capture started");
        Ok(())
    }

    /// Stop all audio capture.
    pub fn stop(&self) {
        self.is_recording.store(false, Ordering::SeqCst);
        info!("Audio capture stopped");
    }

    pub fn is_recording(&self) -> bool {
        self.is_recording.load(Ordering::SeqCst)
    }

    /// Start microphone capture using cpal.
    fn start_microphone(&self) -> Result<(), String> {
        use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

        let host = cpal::default_host();
        let device = host
            .default_input_device()
            .ok_or("No microphone found")?;

        info!("Using microphone: {}", device.name().unwrap_or_default());

        let config = cpal::StreamConfig {
            channels: 1,
            sample_rate: cpal::SampleRate(SAMPLE_RATE),
            buffer_size: cpal::BufferSize::Default,
        };

        let buffer = self.mic_buffer.clone();
        let is_recording = self.is_recording.clone();

        let stream = device
            .build_input_stream(
                &config,
                move |data: &[f32], _: &cpal::InputCallbackInfo| {
                    if is_recording.load(Ordering::Relaxed) {
                        let mut buf = buffer.lock();
                        buf.extend_from_slice(data);
                    }
                },
                move |err| {
                    error!("Microphone stream error: {}", err);
                },
                None,
            )
            .map_err(|e| format!("Failed to build mic stream: {}", e))?;

        stream.play().map_err(|e| format!("Failed to start mic: {}", e))?;

        // Keep stream alive by leaking it (it'll be cleaned up on process exit)
        std::mem::forget(stream);

        info!("Microphone capture started");
        Ok(())
    }

    /// Start system audio capture using ScreenCaptureKit (macOS only).
    #[cfg(target_os = "macos")]
    fn start_system_audio(&self) -> Result<(), String> {
        use screencapturekit::sc_content_filter::SCContentFilter;
        use screencapturekit::sc_shareable_content::SCShareableContent;
        use screencapturekit::sc_stream::SCStream;
        use screencapturekit::sc_stream_configuration::SCStreamConfiguration;

        let buffer = self.system_buffer.clone();
        let is_recording = self.is_recording.clone();

        // Run setup on a background thread since SCK needs the main thread for some ops
        std::thread::spawn(move || {
            let content = match SCShareableContent::try_current() {
                Ok(c) => c,
                Err(e) => {
                    error!("Failed to get shareable content (check Screen Recording permission): {}", e);
                    return;
                }
            };

            // Get the first display for system audio capture
            let displays = content.displays;
            if displays.is_empty() {
                error!("No displays found for system audio capture");
                return;
            }
            let display = &displays[0];

            // Configure for audio-only capture
            let mut config = SCStreamConfiguration::new();
            config.set_captures_audio(true);
            config.set_excludes_current_process_audio(true);
            config.set_channel_count(1);
            config.set_sample_rate(SAMPLE_RATE);

            // Minimal video config (required but we only want audio)
            config.set_width(1);
            config.set_height(1);
            config.set_minimum_frame_interval(
                screencapturekit::cm_time::CMTime {
                    value: 1,
                    timescale: 1, // 1 fps minimum
                    flags: 0,
                    epoch: 0,
                },
            );

            let filter = SCContentFilter::new_with_display_excluding_apps_excepting_windows(
                display,
                &[],
                &[],
            );

            struct AudioHandler {
                buffer: Arc<Mutex<Vec<f32>>>,
                is_recording: Arc<AtomicBool>,
            }

            impl screencapturekit::sc_stream::StreamOutput for AudioHandler {
                fn did_output_sample_buffer(
                    &self,
                    sample_buffer: screencapturekit::cm_sample_buffer::CMSampleBuffer,
                    of_type: screencapturekit::sc_stream::StreamOutputType,
                ) {
                    if of_type != screencapturekit::sc_stream::StreamOutputType::Audio {
                        return;
                    }
                    if !self.is_recording.load(Ordering::Relaxed) {
                        return;
                    }

                    if let Some(audio_buffers) = sample_buffer.get_audio_buffer_list() {
                        for audio_buffer in audio_buffers {
                            let samples: &[f32] = unsafe {
                                std::slice::from_raw_parts(
                                    audio_buffer.data as *const f32,
                                    audio_buffer.data_bytes_size as usize / std::mem::size_of::<f32>(),
                                )
                            };
                            let mut buf = self.buffer.lock();
                            buf.extend_from_slice(samples);
                        }
                    }
                }
            }

            let handler = AudioHandler {
                buffer,
                is_recording,
            };

            match SCStream::new(filter, config, handler) {
                Ok(stream) => {
                    if let Err(e) = stream.start_capture() {
                        error!("Failed to start system audio capture: {}", e);
                    } else {
                        info!("System audio capture started via ScreenCaptureKit");
                        // Keep stream alive
                        std::mem::forget(stream);
                    }
                }
                Err(e) => {
                    error!("Failed to create SCStream: {}", e);
                }
            }
        });

        Ok(())
    }

    /// Start the chunking loop that extracts fixed-size chunks from the audio buffer.
    fn start_chunking_loop(&self, source: AudioSource, buffer: Arc<Mutex<Vec<f32>>>) {
        let sender = self.chunk_sender.clone();
        let is_recording = self.is_recording.clone();

        tokio::spawn(async move {
            let chunk_interval = tokio::time::Duration::from_millis(
                ((CHUNK_DURATION_SECS - CHUNK_OVERLAP_SECS) * 1000.0) as u64,
            );

            loop {
                tokio::time::sleep(chunk_interval).await;

                if !is_recording.load(Ordering::Relaxed) {
                    break;
                }

                let chunk_data = {
                    let mut buf = buffer.lock();
                    if buf.len() < CHUNK_SAMPLES {
                        continue;
                    }

                    // Extract a full chunk
                    let chunk: Vec<f32> = buf[..CHUNK_SAMPLES].to_vec();

                    // Keep overlap for continuity
                    let drain_to = CHUNK_SAMPLES - OVERLAP_SAMPLES;
                    buf.drain(..drain_to);

                    chunk
                };

                let chunk = AudioChunk {
                    samples: chunk_data,
                    source,
                    timestamp_ms: chrono::Utc::now().timestamp_millis(),
                };

                if sender.send(chunk).await.is_err() {
                    warn!("Audio chunk receiver dropped, stopping {:?} chunking", source);
                    break;
                }
            }
        });
    }
}
