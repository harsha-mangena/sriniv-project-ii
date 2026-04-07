//! Transcription pipeline using whisper-rs (whisper.cpp bindings).
//!
//! Processes audio chunks from the audio capture module and produces
//! timestamped transcript segments. Results are emitted as Tauri events
//! and sent to the backend WebSocket.

use crate::audio::{AudioChunk, AudioSource};
use log::{error, info, warn};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;
use tauri::Emitter;
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

/// Path to the whisper model file.
const MODEL_FILENAME: &str = "ggml-base.en.bin";

/// URL to download the whisper model.
const MODEL_URL: &str = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin";

/// A timestamped transcript segment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranscriptSegment {
    pub text: String,
    pub speaker: String,
    pub start_ms: i64,
    pub end_ms: i64,
    pub timestamp_ms: i64,
}

/// Event payload emitted to the overlay frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranscriptEvent {
    pub segments: Vec<TranscriptSegment>,
    pub full_text: String,
    pub speaker: String,
}

/// Manages the whisper transcription pipeline.
pub struct TranscriptionPipeline {
    context: Arc<Mutex<Option<WhisperContext>>>,
    transcript: Arc<Mutex<Vec<TranscriptSegment>>>,
    model_path: PathBuf,
}

impl TranscriptionPipeline {
    pub fn new() -> Self {
        let model_dir = dirs::data_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("interviewpilot")
            .join("models");

        std::fs::create_dir_all(&model_dir).ok();

        Self {
            context: Arc::new(Mutex::new(None)),
            transcript: Arc::new(Mutex::new(Vec::new())),
            model_path: model_dir.join(MODEL_FILENAME),
        }
    }

    /// Initialize the whisper model. Downloads if not present.
    pub async fn initialize(&self, app_handle: &tauri::AppHandle) -> Result<(), String> {
        if !self.model_path.exists() {
            self.download_model(app_handle).await?;
        }

        let model_path = self.model_path.clone();
        let context = self.context.clone();

        // Load model on blocking thread (CPU-intensive)
        tokio::task::spawn_blocking(move || {
            let params = WhisperContextParameters::default();
            match WhisperContext::new_with_params(
                model_path.to_str().unwrap_or_default(),
                params,
            ) {
                Ok(ctx) => {
                    *context.lock() = Some(ctx);
                    info!("Whisper model loaded successfully");
                    Ok(())
                }
                Err(e) => {
                    error!("Failed to load whisper model: {}", e);
                    Err(format!("Failed to load whisper model: {}", e))
                }
            }
        })
        .await
        .map_err(|e| format!("Model loading task failed: {}", e))?
    }

    /// Download the whisper model with progress updates.
    async fn download_model(&self, app_handle: &tauri::AppHandle) -> Result<(), String> {
        info!("Downloading whisper model from {}", MODEL_URL);
        app_handle
            .emit("model-download-start", MODEL_URL)
            .ok();

        let response = reqwest::get(MODEL_URL)
            .await
            .map_err(|e| format!("Failed to download model: {}", e))?;

        let total_size = response.content_length().unwrap_or(0);
        let mut downloaded: u64 = 0;

        let bytes = response
            .bytes()
            .await
            .map_err(|e| format!("Failed to read model data: {}", e))?;

        downloaded = bytes.len() as u64;

        // Save to disk
        std::fs::write(&self.model_path, &bytes)
            .map_err(|e| format!("Failed to save model: {}", e))?;

        app_handle
            .emit(
                "model-download-progress",
                serde_json::json!({
                    "downloaded": downloaded,
                    "total": total_size,
                    "percent": if total_size > 0 { (downloaded * 100) / total_size } else { 100 }
                }),
            )
            .ok();

        app_handle.emit("model-download-complete", ()).ok();

        info!(
            "Whisper model downloaded ({:.1} MB)",
            downloaded as f64 / 1_048_576.0
        );
        Ok(())
    }

    /// Process an audio chunk and return transcript segments.
    pub async fn transcribe(&self, chunk: AudioChunk) -> Result<Vec<TranscriptSegment>, String> {
        let context = self.context.clone();
        let transcript_store = self.transcript.clone();

        let segments = tokio::task::spawn_blocking(move || {
            let ctx_guard = context.lock();
            let ctx = ctx_guard
                .as_ref()
                .ok_or_else(|| "Whisper model not initialized".to_string())?;

            let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
            params.set_language(Some("en"));
            params.set_print_progress(false);
            params.set_print_realtime(false);
            params.set_print_timestamps(false);
            params.set_no_context(true);
            params.set_single_segment(false);

            // Create a new state for this transcription
            let mut state = ctx.create_state().map_err(|e| format!("Failed to create state: {}", e))?;

            state
                .full(params, &chunk.samples)
                .map_err(|e| format!("Transcription failed: {}", e))?;

            let num_segments = state.full_n_segments().map_err(|e| format!("Failed to get segments: {}", e))?;
            let speaker = match chunk.source {
                AudioSource::System => "interviewer",
                AudioSource::Microphone => "user",
            };

            let mut segments = Vec::new();
            for i in 0..num_segments {
                let text = state
                    .full_get_segment_text(i)
                    .map_err(|e| format!("Failed to get segment text: {}", e))?;
                let text = text.trim().to_string();

                if text.is_empty() {
                    continue;
                }

                let start = state.full_get_segment_t0(i).unwrap_or(0);
                let end = state.full_get_segment_t1(i).unwrap_or(0);

                segments.push(TranscriptSegment {
                    text,
                    speaker: speaker.to_string(),
                    start_ms: (start as i64) * 10, // whisper uses centiseconds
                    end_ms: (end as i64) * 10,
                    timestamp_ms: chunk.timestamp_ms,
                });
            }

            // Store in transcript history
            {
                let mut store = transcript_store.lock();
                store.extend(segments.clone());
                // Keep last 500 segments
                if store.len() > 500 {
                    let drain_to = store.len() - 500;
                    store.drain(..drain_to);
                }
            }

            Ok::<Vec<TranscriptSegment>, String>(segments)
        })
        .await
        .map_err(|e| format!("Transcription task panicked: {}", e))??;

        Ok(segments)
    }

    /// Emit transcript segments as a Tauri event to the overlay.
    pub fn emit_transcript(
        app_handle: &tauri::AppHandle,
        segments: &[TranscriptSegment],
    ) {
        if segments.is_empty() {
            return;
        }

        let full_text = segments
            .iter()
            .map(|s| s.text.as_str())
            .collect::<Vec<_>>()
            .join(" ");

        let speaker = segments
            .first()
            .map(|s| s.speaker.clone())
            .unwrap_or_default();

        let event = TranscriptEvent {
            segments: segments.to_vec(),
            full_text,
            speaker,
        };

        if let Err(e) = app_handle.emit("transcript-update", &event) {
            warn!("Failed to emit transcript event: {}", e);
        }
    }

    /// Get the full transcript history.
    pub fn get_transcript(&self) -> Vec<TranscriptSegment> {
        self.transcript.lock().clone()
    }

    /// Get recent transcript as a formatted string (for sending to backend).
    pub fn get_recent_text(&self, max_segments: usize) -> String {
        let transcript = self.transcript.lock();
        let start = transcript.len().saturating_sub(max_segments);
        transcript[start..]
            .iter()
            .map(|s| format!("[{}]: {}", s.speaker, s.text))
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Clear transcript history.
    pub fn clear(&self) {
        self.transcript.lock().clear();
    }
}
