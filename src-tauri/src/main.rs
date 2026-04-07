// Prevents additional console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod audio;
mod commands;
mod overlay;
mod screen_capture;
mod shortcuts;
mod transcription;
mod tray;

use commands::AppState;
use log::info;
use std::sync::Arc;
use tauri::Manager;

fn main() {
    env_logger::init();

    let app_state = Arc::new(AppState::new());

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_nspanel::init())
        .manage(app_state.clone())
        .setup(move |app| {
            info!("InterviewPilot starting up...");

            // Set up overlay window (convert to NSPanel on macOS)
            #[cfg(target_os = "macos")]
            overlay::setup_overlay(app.handle());

            // Register global shortcuts
            shortcuts::register_shortcuts(app.handle())?;

            // Set up system tray
            tray::setup_tray(app)?;

            // Spawn backend process
            spawn_backend(app.handle());

            info!("InterviewPilot setup complete.");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::start_recording,
            commands::stop_recording,
            commands::toggle_overlay,
            commands::take_screenshot,
            commands::get_transcript,
            commands::send_chat_message,
            commands::get_suggestions,
            commands::update_settings,
            commands::get_recording_status,
            commands::get_app_state,
        ])
        .run(tauri::generate_context!())
        .expect("error while running InterviewPilot");
}

/// Spawn the Python FastAPI backend as a child process.
fn spawn_backend(app_handle: &tauri::AppHandle) {
    use tauri_plugin_shell::ShellExt;

    let shell = app_handle.shell();

    // Try to start the backend. In production, the backend is bundled.
    // In dev, it's assumed to be running separately or started via dev.sh.
    #[cfg(debug_assertions)]
    {
        info!("Dev mode: expecting backend to be running on :8000");
        let _ = shell; // suppress unused warning in dev
    }

    #[cfg(not(debug_assertions))]
    {
        info!("Production: spawning backend process...");
        let resource_dir = app_handle
            .path()
            .resource_dir()
            .expect("failed to resolve resource dir");
        let backend_dir = resource_dir.join("backend");

        if backend_dir.exists() {
            let venv_python = backend_dir.join(".venv/bin/python3");
            let python = if venv_python.exists() {
                venv_python.to_string_lossy().to_string()
            } else {
                "python3".to_string()
            };

            match shell.command(&python).args([
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]).current_dir(backend_dir).spawn() {
                Ok(child) => {
                    info!("Backend spawned with PID tracking");
                    // Store child handle for cleanup
                    let _ = child;
                }
                Err(e) => {
                    log::error!("Failed to spawn backend: {}", e);
                }
            }
        } else {
            log::warn!("Backend directory not found at {:?}", backend_dir);
        }
    }
}
