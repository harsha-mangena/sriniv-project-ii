//! Screen capture module for periodic/on-demand screenshots.
//!
//! Captures screenshots, extracts text via the backend's LLM-based OCR,
//! and maintains a rolling buffer of recent captures for context.

use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use log::{error, info, warn};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;
use uuid::Uuid;

/// Maximum number of screenshots to keep in the buffer.
const MAX_CAPTURES: usize = 5;

/// Information about a captured screenshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenshotInfo {
    pub id: String,
    pub path: String,
    pub timestamp_ms: i64,
    pub width: u32,
    pub height: u32,
    pub ocr_text: Option<String>,
    pub base64_thumbnail: Option<String>,
}

/// Manages screen capture and OCR context buffer.
pub struct ScreenCaptureManager {
    captures: Arc<Mutex<Vec<ScreenshotInfo>>>,
    capture_dir: PathBuf,
    backend_url: String,
}

impl ScreenCaptureManager {
    pub fn new(backend_url: String) -> Self {
        let capture_dir = std::env::temp_dir().join("interviewpilot_captures");
        std::fs::create_dir_all(&capture_dir).ok();

        Self {
            captures: Arc::new(Mutex::new(Vec::with_capacity(MAX_CAPTURES + 1))),
            capture_dir,
            backend_url,
        }
    }

    /// Take a screenshot of the primary display.
    pub async fn capture(&self) -> Result<ScreenshotInfo, String> {
        let capture_dir = self.capture_dir.clone();
        let backend_url = self.backend_url.clone();

        // Screenshot capture must run on a blocking thread
        let info = tokio::task::spawn_blocking(move || {
            capture_screenshot(&capture_dir)
        })
        .await
        .map_err(|e| format!("Screenshot task failed: {}", e))?
        .map_err(|e| format!("Screenshot capture failed: {}", e))?;

        // Try OCR via backend
        let info = self.run_ocr(info, &backend_url).await;

        // Add to buffer, maintaining max size
        {
            let mut captures = self.captures.lock();
            captures.push(info.clone());

            // Remove oldest if over limit
            while captures.len() > MAX_CAPTURES {
                let removed = captures.remove(0);
                // Clean up old file
                std::fs::remove_file(&removed.path).ok();
            }
        }

        info!("Screenshot captured: {}", info.id);
        Ok(info)
    }

    /// Get the latest screenshot context (OCR text from recent captures).
    pub fn get_context(&self) -> Vec<ScreenshotInfo> {
        self.captures.lock().clone()
    }

    /// Get combined OCR text from recent captures.
    pub fn get_ocr_context(&self) -> String {
        let captures = self.captures.lock();
        captures
            .iter()
            .filter_map(|c| c.ocr_text.as_deref())
            .collect::<Vec<_>>()
            .join("\n---\n")
    }

    /// Clean up all capture files.
    pub fn cleanup(&self) {
        let captures = self.captures.lock();
        for capture in captures.iter() {
            std::fs::remove_file(&capture.path).ok();
        }
        std::fs::remove_dir_all(&self.capture_dir).ok();
        info!("Cleaned up screenshot captures");
    }

    /// Run OCR by sending the screenshot to the backend for LLM-based text extraction.
    async fn run_ocr(&self, mut info: ScreenshotInfo, backend_url: &str) -> ScreenshotInfo {
        let image_data = match std::fs::read(&info.path) {
            Ok(data) => data,
            Err(e) => {
                warn!("Failed to read screenshot for OCR: {}", e);
                return info;
            }
        };

        let b64 = BASE64.encode(&image_data);

        // Create a thumbnail (smaller base64 for the overlay UI)
        info.base64_thumbnail = Some(create_thumbnail_b64(&info.path));

        // Send to backend for OCR
        let client = reqwest::Client::new();
        let url = format!("{}/api/realtime/ocr", backend_url);

        match client
            .post(&url)
            .json(&serde_json::json!({
                "image_base64": b64,
                "format": "png"
            }))
            .timeout(std::time::Duration::from_secs(10))
            .send()
            .await
        {
            Ok(resp) => {
                if resp.status().is_success() {
                    if let Ok(body) = resp.json::<serde_json::Value>().await {
                        info.ocr_text = body.get("text").and_then(|t| t.as_str()).map(String::from);
                    }
                } else {
                    warn!("OCR endpoint returned {}", resp.status());
                }
            }
            Err(e) => {
                warn!("Failed to call OCR endpoint: {}", e);
            }
        }

        info
    }
}

impl Drop for ScreenCaptureManager {
    fn drop(&mut self) {
        self.cleanup();
    }
}

/// Capture a screenshot of the primary display using the `screenshots` crate.
fn capture_screenshot(capture_dir: &PathBuf) -> Result<ScreenshotInfo, String> {
    let screens = screenshots::Screen::all().map_err(|e| format!("Failed to list screens: {}", e))?;

    let screen = screens
        .into_iter()
        .find(|s| s.display_info.is_primary)
        .or_else(|| screenshots::Screen::all().ok()?.into_iter().next())
        .ok_or("No display found")?;

    let image = screen
        .capture()
        .map_err(|e| format!("Failed to capture screen: {}", e))?;

    let id = Uuid::new_v4().to_string();
    let filename = format!("capture_{}.png", &id[..8]);
    let path = capture_dir.join(&filename);

    image
        .save(&path)
        .map_err(|e| format!("Failed to save screenshot: {}", e))?;

    Ok(ScreenshotInfo {
        id,
        path: path.to_string_lossy().to_string(),
        timestamp_ms: chrono::Utc::now().timestamp_millis(),
        width: image.width(),
        height: image.height(),
        ocr_text: None,
        base64_thumbnail: None,
    })
}

/// Create a small base64-encoded thumbnail for the overlay preview.
fn create_thumbnail_b64(path: &str) -> String {
    match image::open(path) {
        Ok(img) => {
            let thumb = img.thumbnail(200, 150);
            let mut buf = Vec::new();
            let mut cursor = std::io::Cursor::new(&mut buf);
            if thumb
                .write_to(&mut cursor, image::ImageFormat::Png)
                .is_ok()
            {
                BASE64.encode(&buf)
            } else {
                String::new()
            }
        }
        Err(e) => {
            warn!("Failed to create thumbnail: {}", e);
            String::new()
        }
    }
}
