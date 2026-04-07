//! System tray menu and icon management.
//!
//! Provides a system tray with controls for session management, overlay visibility,
//! and application state. The tray icon changes based on recording state.

use log::{error, info};
use std::sync::Arc;
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    Emitter, Manager,
};

use crate::commands::AppState;
use crate::overlay;

/// Tray icon identifiers for different states.
const TRAY_ID: &str = "main-tray";

/// Set up the system tray with menu items.
pub fn setup_tray(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let handle = app.handle();

    // Create menu items
    let start_session = MenuItem::with_id(handle, "start_session", "Start Session", true, None::<&str>)?;
    let stop_session = MenuItem::with_id(handle, "stop_session", "Stop Session", true, None::<&str>)?;
    let show_overlay = MenuItem::with_id(handle, "show_overlay", "Show Overlay", true, None::<&str>)?;
    let hide_overlay = MenuItem::with_id(handle, "hide_overlay", "Hide Overlay", true, None::<&str>)?;
    let open_main = MenuItem::with_id(handle, "open_main", "Open InterviewPilot", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(handle)?;
    let settings = MenuItem::with_id(handle, "settings", "Settings", true, None::<&str>)?;
    let quit = MenuItem::with_id(handle, "quit", "Quit", true, None::<&str>)?;

    let menu = Menu::with_items(
        handle,
        &[
            &start_session,
            &stop_session,
            &show_overlay,
            &hide_overlay,
            &open_main,
            &separator,
            &settings,
            &quit,
        ],
    )?;

    let _tray = TrayIconBuilder::with_id(TRAY_ID)
        .menu(&menu)
        .icon(app.default_window_icon().cloned().unwrap_or_else(|| {
            tauri::image::Image::new(&[], 0, 0)
        }))
        .icon_as_template(true)
        .tooltip("InterviewPilot")
        .on_menu_event(move |app, event| {
            handle_tray_event(app, event.id.as_ref());
        })
        .build(app)?;

    info!("System tray configured");
    Ok(())
}

/// Handle tray menu item clicks.
fn handle_tray_event(app: &tauri::AppHandle, item_id: &str) {
    match item_id {
        "start_session" => {
            info!("Tray: start session");
            let state = app.state::<Arc<AppState>>();
            match state.audio_capture.start() {
                Ok(()) => {
                    app.emit("recording-status", true).ok();
                    update_tray_tooltip(app, "InterviewPilot - Recording");
                }
                Err(e) => {
                    error!("Failed to start session: {}", e);
                    app.emit("recording-error", e).ok();
                }
            }
        }

        "stop_session" => {
            info!("Tray: stop session");
            let state = app.state::<Arc<AppState>>();
            state.audio_capture.stop();
            app.emit("recording-status", false).ok();
            update_tray_tooltip(app, "InterviewPilot - Idle");
        }

        "show_overlay" => {
            info!("Tray: show overlay");
            if let Some(overlay) = app.get_webview_window("overlay") {
                overlay.show().ok();
                overlay.set_focus().ok();
            }
        }

        "hide_overlay" => {
            info!("Tray: hide overlay");
            if let Some(overlay) = app.get_webview_window("overlay") {
                overlay.hide().ok();
            }
        }

        "open_main" => {
            info!("Tray: open main window");
            if let Some(main) = app.get_webview_window("main") {
                main.show().ok();
                main.set_focus().ok();
            }
        }

        "settings" => {
            info!("Tray: open settings");
            if let Some(main) = app.get_webview_window("main") {
                main.show().ok();
                main.set_focus().ok();
                // Navigate to settings page
                main.eval("window.location.hash = '/settings'").ok();
            }
        }

        "quit" => {
            info!("Tray: quit");
            // Clean up resources
            let state = app.state::<Arc<AppState>>();
            state.audio_capture.stop();
            state.screen_capture.cleanup();
            std::process::exit(0);
        }

        _ => {
            info!("Tray: unknown menu item: {}", item_id);
        }
    }
}

/// Update the tray tooltip text.
fn update_tray_tooltip(app: &tauri::AppHandle, tooltip: &str) {
    if let Some(tray) = app.tray_by_id(TRAY_ID) {
        tray.set_tooltip(Some(tooltip)).ok();
    }
}
