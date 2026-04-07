//! Tauri IPC commands exposed to the frontend via `invoke()`.
//!
//! These commands bridge the React frontend and the Rust backend,
//! providing access to audio capture, screen capture, transcription,
//! overlay control, and backend communication.

use crate::audio::{AudioCapture, AudioChunk};
use crate::overlay;
use crate::screen_capture::{ScreenCaptureManager, ScreenshotInfo};
use crate::transcription::{TranscriptSegment, TranscriptionPipeline};
use log::{error, info};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::{Emitter, State};

/// Backend API base URL.
const BACKEND_URL: &str = "http://127.0.0.1:8000";

/// Application-wide shared state.
pub struct AppState {
    pub audio_capture: AudioCapture,
    pub screen_capture: Arc<ScreenCaptureManager>,
    pub transcription: Arc<TranscriptionPipeline>,
    /// Channel receiver for audio chunks (consumed by the transcription loop).
    chunk_receiver: tokio::sync::Mutex<Option<tokio::sync::mpsc::Receiver<AudioChunk>>>,
}

impl AppState {
    pub fn new() -> Self {
        let (chunk_tx, chunk_rx) = tokio::sync::mpsc::channel::<AudioChunk>(64);

        Self {
            audio_capture: AudioCapture::new(chunk_tx),
            screen_capture: Arc::new(ScreenCaptureManager::new(BACKEND_URL.to_string())),
            transcription: Arc::new(TranscriptionPipeline::new()),
            chunk_receiver: tokio::sync::Mutex::new(Some(chunk_rx)),
        }
    }

    /// Start the transcription processing loop.
    /// Takes the chunk receiver (can only be called once).
    pub async fn start_transcription_loop(&self, app_handle: tauri::AppHandle) {
        let mut rx_guard = self.chunk_receiver.lock().await;
        let Some(mut receiver) = rx_guard.take() else {
            info!("Transcription loop already started");
            return;
        };
        drop(rx_guard);

        let transcription = self.transcription.clone();
        let handle = app_handle.clone();

        tokio::spawn(async move {
            info!("Transcription loop started");

            while let Some(chunk) = receiver.recv().await {
                match transcription.transcribe(chunk).await {
                    Ok(segments) if !segments.is_empty() => {
                        // Emit to overlay UI
                        TranscriptionPipeline::emit_transcript(&handle, &segments);

                        // Send to backend WebSocket
                        send_transcript_to_backend(&segments).await;
                    }
                    Ok(_) => {} // Empty transcription, skip
                    Err(e) => {
                        error!("Transcription error: {}", e);
                    }
                }
            }

            info!("Transcription loop ended");
        });
    }
}

/// Settings that can be updated from the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub overlay_opacity: Option<f64>,
    pub overlay_position: Option<OverlayPosition>,
    pub shortcuts_enabled: Option<bool>,
    pub auto_screenshot: Option<bool>,
    pub screenshot_interval_secs: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverlayPosition {
    pub x: f64,
    pub y: f64,
}

/// Suggestion from the backend LLM.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Suggestion {
    pub text: String,
    pub confidence: f64,
    pub question: Option<String>,
}

/// Current app state summary for the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppStateSummary {
    pub is_recording: bool,
    pub transcript_count: usize,
    pub screenshot_count: usize,
    pub model_loaded: bool,
}

// --- Tauri Commands ---

/// Start audio recording (system + microphone).
#[tauri::command]
pub async fn start_recording(
    state: State<'_, Arc<AppState>>,
    app_handle: tauri::AppHandle,
) -> Result<(), String> {
    info!("Command: start_recording");

    // Initialize transcription model if needed
    state.transcription.initialize(&app_handle).await?;

    // Start the transcription processing loop
    state.start_transcription_loop(app_handle.clone()).await;

    // Start audio capture
    state.audio_capture.start()?;

    app_handle.emit("recording-status", true).ok();
    Ok(())
}

/// Stop audio recording.
#[tauri::command]
pub async fn stop_recording(
    state: State<'_, Arc<AppState>>,
    app_handle: tauri::AppHandle,
) -> Result<(), String> {
    info!("Command: stop_recording");

    state.audio_capture.stop();
    app_handle.emit("recording-status", false).ok();
    Ok(())
}

/// Toggle overlay window visibility.
#[tauri::command]
pub async fn toggle_overlay(app_handle: tauri::AppHandle) -> Result<(), String> {
    info!("Command: toggle_overlay");
    overlay::toggle_overlay_visibility(&app_handle)
}

/// Take a screenshot and run OCR.
#[tauri::command]
pub async fn take_screenshot(
    state: State<'_, Arc<AppState>>,
    app_handle: tauri::AppHandle,
) -> Result<ScreenshotInfo, String> {
    info!("Command: take_screenshot");

    let info = state.screen_capture.capture().await?;
    app_handle.emit("screenshot-taken", &info).ok();
    Ok(info)
}

/// Get the current transcript history.
#[tauri::command]
pub async fn get_transcript(
    state: State<'_, Arc<AppState>>,
) -> Result<Vec<TranscriptSegment>, String> {
    Ok(state.transcription.get_transcript())
}

/// Send a chat message to the backend for AI response.
/// This is the "What should I say?" feature.
#[tauri::command]
pub async fn send_chat_message(
    state: State<'_, Arc<AppState>>,
    message: String,
) -> Result<String, String> {
    info!("Command: send_chat_message");

    let recent_transcript = state.transcription.get_recent_text(20);
    let screen_context = state.screen_capture.get_ocr_context();

    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/api/realtime/suggest", BACKEND_URL))
        .json(&serde_json::json!({
            "question": message,
            "transcript": recent_transcript,
            "screen_context": screen_context,
        }))
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("Failed to reach backend: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Backend returned error: {}", response.status()));
    }

    let body: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    body.get("suggestion")
        .and_then(|s| s.as_str())
        .map(String::from)
        .ok_or_else(|| "No suggestion in response".to_string())
}

/// Get AI suggestions based on detected questions.
#[tauri::command]
pub async fn get_suggestions(
    state: State<'_, Arc<AppState>>,
) -> Result<Vec<Suggestion>, String> {
    let recent_transcript = state.transcription.get_recent_text(10);

    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/api/realtime/suggest", BACKEND_URL))
        .json(&serde_json::json!({
            "question": "What key points should I address based on the conversation?",
            "transcript": recent_transcript,
            "screen_context": state.screen_capture.get_ocr_context(),
        }))
        .timeout(std::time::Duration::from_secs(15))
        .send()
        .await
        .map_err(|e| format!("Backend request failed: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Backend error: {}", response.status()));
    }

    let body: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let suggestion_text = body
        .get("suggestion")
        .and_then(|s| s.as_str())
        .unwrap_or_default();

    Ok(vec![Suggestion {
        text: suggestion_text.to_string(),
        confidence: 0.8,
        question: None,
    }])
}

/// Update application settings.
#[tauri::command]
pub async fn update_settings(
    app_handle: tauri::AppHandle,
    settings: AppSettings,
) -> Result<(), String> {
    info!("Command: update_settings");

    if let Some(opacity) = settings.overlay_opacity {
        if let Some(overlay) = app_handle.get_webview_window("overlay") {
            // Opacity is handled via CSS in the overlay window
            overlay
                .eval(&format!(
                    "document.body.style.opacity = '{}'",
                    opacity.clamp(0.1, 1.0)
                ))
                .map_err(|e| e.to_string())?;
        }
    }

    if let Some(pos) = settings.overlay_position {
        overlay::move_overlay(&app_handle, pos.x as i32, pos.y as i32)?;
    }

    Ok(())
}

/// Get current recording status.
#[tauri::command]
pub async fn get_recording_status(
    state: State<'_, Arc<AppState>>,
) -> Result<bool, String> {
    Ok(state.audio_capture.is_recording())
}

/// Get a summary of the current app state.
#[tauri::command]
pub async fn get_app_state(
    state: State<'_, Arc<AppState>>,
) -> Result<AppStateSummary, String> {
    Ok(AppStateSummary {
        is_recording: state.audio_capture.is_recording(),
        transcript_count: state.transcription.get_transcript().len(),
        screenshot_count: state.screen_capture.get_context().len(),
        model_loaded: true, // simplified check
    })
}

/// Send transcript segments to the backend WebSocket.
async fn send_transcript_to_backend(segments: &[TranscriptSegment]) {
    let client = reqwest::Client::new();

    for segment in segments {
        let payload = serde_json::json!({
            "type": "transcript",
            "text": segment.text,
            "speaker": segment.speaker,
            "timestamp_ms": segment.timestamp_ms,
        });

        // Post to backend REST endpoint as fallback (WebSocket is primary)
        if let Err(e) = client
            .post(format!("{}/api/realtime/transcript", BACKEND_URL))
            .json(&payload)
            .timeout(std::time::Duration::from_secs(5))
            .send()
            .await
        {
            // This is expected to fail sometimes; the WebSocket is the primary transport
            log::debug!("Failed to send transcript to backend: {}", e);
        }
    }
}
