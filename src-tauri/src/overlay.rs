//! Overlay window management using NSPanel for above-fullscreen behavior.
//!
//! Converts the Tauri overlay window to a macOS NSPanel, which can float above
//! fullscreen apps and be invisible to screen recording/sharing.

use log::{error, info};
use tauri::Manager;

#[cfg(target_os = "macos")]
use tauri_nspanel::ManagerExt;

/// Set up the overlay window as an NSPanel on macOS.
///
/// This converts the standard window to an NSPanel with:
/// - Above-fullscreen capability
/// - Content protection (invisible to screen recording)
/// - All-spaces visibility
/// - Click-through when unfocused
#[cfg(target_os = "macos")]
pub fn setup_overlay(app_handle: &tauri::AppHandle) {
    use tauri_nspanel::WebviewWindowExt;

    let Some(overlay) = app_handle.get_webview_window("overlay") else {
        error!("Overlay window not found in config");
        return;
    };

    // Convert to NSPanel for above-fullscreen behavior
    let panel = match overlay.to_panel() {
        Ok(p) => p,
        Err(e) => {
            error!("Failed to convert overlay to NSPanel: {}", e);
            return;
        }
    };

    // Collection behavior: visible on all spaces, usable alongside fullscreen apps
    // NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
    // NSWindowCollectionBehaviorStationary = 1 << 4
    // NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8
    let can_join_all_spaces: u32 = 1 << 0;
    let stationary: u32 = 1 << 4;
    let fullscreen_auxiliary: u32 = 1 << 8;
    panel.set_collection_behaviour(
        tauri_nspanel::raw_nspanel::NSWindowCollectionBehavior(
            (can_join_all_spaces | stationary | fullscreen_auxiliary) as isize,
        ),
    );

    // NSMainMenuWindowLevel = 24, we go one above
    panel.set_level(25);

    // Allow the panel to be key window (receive keyboard input)
    panel.set_becomes_key_only_if_needed(false);

    // Content protection: invisible to screen recording/sharing
    if let Err(e) = overlay.set_content_protected(true) {
        error!("Failed to set content protection: {}", e);
    }

    info!("Overlay NSPanel configured successfully");
}

#[cfg(not(target_os = "macos"))]
pub fn setup_overlay(_app_handle: &tauri::AppHandle) {
    info!("Overlay NSPanel setup skipped (not macOS)");
}

/// Toggle overlay window visibility.
pub fn toggle_overlay_visibility(app_handle: &tauri::AppHandle) -> Result<(), String> {
    let overlay = app_handle
        .get_webview_window("overlay")
        .ok_or("Overlay window not found")?;

    if overlay.is_visible().unwrap_or(false) {
        overlay.hide().map_err(|e| e.to_string())?;
        info!("Overlay hidden");
    } else {
        overlay.show().map_err(|e| e.to_string())?;
        overlay.set_focus().map_err(|e| e.to_string())?;
        info!("Overlay shown");
    }

    Ok(())
}

/// Move overlay window by delta pixels.
pub fn move_overlay(app_handle: &tauri::AppHandle, dx: i32, dy: i32) -> Result<(), String> {
    let overlay = app_handle
        .get_webview_window("overlay")
        .ok_or("Overlay window not found")?;

    let pos = overlay.outer_position().map_err(|e| e.to_string())?;
    let new_x = pos.x + dx;
    let new_y = pos.y + dy;

    overlay
        .set_position(tauri::PhysicalPosition::new(new_x, new_y))
        .map_err(|e| e.to_string())?;

    Ok(())
}

/// Resize overlay window.
pub fn resize_overlay(app_handle: &tauri::AppHandle, width: u32, height: u32) -> Result<(), String> {
    let overlay = app_handle
        .get_webview_window("overlay")
        .ok_or("Overlay window not found")?;

    overlay
        .set_size(tauri::PhysicalSize::new(width, height))
        .map_err(|e| e.to_string())?;

    Ok(())
}
