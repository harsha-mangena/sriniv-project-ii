//! Global keyboard shortcut handlers.
//!
//! Registers system-wide shortcuts for controlling the overlay, recording,
//! screenshots, and window management.

use log::{error, info};
use std::sync::Arc;
use tauri::{Emitter, Manager};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

use crate::commands::AppState;
use crate::overlay;

/// The step size (in pixels) for moving the overlay with arrow keys.
const MOVE_STEP: i32 = 50;

/// Register all global shortcuts for the application.
pub fn register_shortcuts(app_handle: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let app = app_handle.clone();

    app_handle.plugin(
        tauri_plugin_global_shortcut::Builder::new()
            .with_handler(move |_app, shortcut, event| {
                if event.state != ShortcutState::Pressed {
                    return;
                }
                handle_shortcut(&app, shortcut);
            })
            .build(),
    )?;

    // Register individual shortcuts
    let shortcuts = vec![
        // Cmd+\ — Toggle overlay visibility
        Shortcut::new(Some(Modifiers::SUPER), Code::Backslash),
        // Cmd+Shift+Space — Toggle recording
        Shortcut::new(Some(Modifiers::SUPER | Modifiers::SHIFT), Code::Space),
        // Cmd+H — Take screenshot (override system hide)
        Shortcut::new(Some(Modifiers::SUPER), Code::KeyH),
        // Cmd+Enter — Focus overlay chat input
        Shortcut::new(Some(Modifiers::SUPER), Code::Enter),
        // Cmd+Arrow keys — Move overlay
        Shortcut::new(Some(Modifiers::SUPER), Code::ArrowUp),
        Shortcut::new(Some(Modifiers::SUPER), Code::ArrowDown),
        Shortcut::new(Some(Modifiers::SUPER), Code::ArrowLeft),
        Shortcut::new(Some(Modifiers::SUPER), Code::ArrowRight),
        // Cmd+R — Clear context / reset
        Shortcut::new(Some(Modifiers::SUPER), Code::KeyR),
    ];

    for shortcut in &shortcuts {
        if let Err(e) = app_handle.global_shortcut().register(*shortcut) {
            error!("Failed to register shortcut {:?}: {}", shortcut, e);
        }
    }

    info!("Global shortcuts registered");
    Ok(())
}

/// Handle a triggered global shortcut.
fn handle_shortcut(app: &tauri::AppHandle, shortcut: &Shortcut) {
    let mods = shortcut.mods;
    let code = shortcut.key;

    match (mods, code) {
        // Cmd+\ — Toggle overlay
        (Some(m), Code::Backslash) if m.contains(Modifiers::SUPER) => {
            info!("Shortcut: toggle overlay");
            if let Err(e) = overlay::toggle_overlay_visibility(app) {
                error!("Failed to toggle overlay: {}", e);
            }
        }

        // Cmd+Shift+Space — Toggle recording
        (Some(m), Code::Space)
            if m.contains(Modifiers::SUPER) && m.contains(Modifiers::SHIFT) =>
        {
            info!("Shortcut: toggle recording");
            let state = app.state::<Arc<AppState>>();
            let is_recording = state.audio_capture.is_recording();

            if is_recording {
                state.audio_capture.stop();
                app.emit("recording-status", false).ok();
            } else {
                match state.audio_capture.start() {
                    Ok(()) => {
                        app.emit("recording-status", true).ok();
                    }
                    Err(e) => {
                        error!("Failed to start recording: {}", e);
                        app.emit("recording-error", e).ok();
                    }
                }
            }
        }

        // Cmd+H — Take screenshot
        (Some(m), Code::KeyH) if m.contains(Modifiers::SUPER) => {
            info!("Shortcut: take screenshot");
            let state = app.state::<Arc<AppState>>();
            let screen_capture = state.screen_capture.clone();
            let app_clone = app.clone();

            tokio::spawn(async move {
                match screen_capture.capture().await {
                    Ok(info) => {
                        app_clone.emit("screenshot-taken", &info).ok();
                    }
                    Err(e) => {
                        error!("Screenshot failed: {}", e);
                    }
                }
            });
        }

        // Cmd+Enter — Focus chat input in overlay
        (Some(m), Code::Enter) if m.contains(Modifiers::SUPER) => {
            info!("Shortcut: focus overlay chat");
            // Show overlay and signal it to focus the chat input
            overlay::toggle_overlay_visibility(app).ok();
            app.emit("focus-chat-input", ()).ok();
        }

        // Cmd+Arrow keys — Move overlay
        (Some(m), Code::ArrowUp) if m.contains(Modifiers::SUPER) => {
            overlay::move_overlay(app, 0, -MOVE_STEP).ok();
        }
        (Some(m), Code::ArrowDown) if m.contains(Modifiers::SUPER) => {
            overlay::move_overlay(app, 0, MOVE_STEP).ok();
        }
        (Some(m), Code::ArrowLeft) if m.contains(Modifiers::SUPER) => {
            overlay::move_overlay(app, -MOVE_STEP, 0).ok();
        }
        (Some(m), Code::ArrowRight) if m.contains(Modifiers::SUPER) => {
            overlay::move_overlay(app, MOVE_STEP, 0).ok();
        }

        // Cmd+R — Clear context / reset
        (Some(m), Code::KeyR) if m.contains(Modifiers::SUPER) => {
            info!("Shortcut: clear context");
            let state = app.state::<Arc<AppState>>();
            state.transcription.clear();
            app.emit("context-cleared", ()).ok();
        }

        _ => {}
    }
}
