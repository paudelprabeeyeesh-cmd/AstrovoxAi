use astrovox_tauri::shell::setup_system_tray;
use astrovox_tauri::chat::setup_chat_window;
use astrovox_tauri::updater::check_for_updates;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![
            astrovox_tauri::chat::send_message,
            astrovox_tauri::chat::get_conversation,
            astrovox_tauri::chat::clear_conversation,
            astrovox_tauri::chat::clear_all_conversations,
            astrovox_tauri::settings::get_settings,
            astrovox_tauri::settings::save_settings,
            astrovox_tauri::updater::check_updates,
            astrovox_tauri::updater::install_update,
            astrovox_tauri::auth::authenticate,
            astrovox_tauri::auth::signup,
            astrovox_tauri::auth::refresh_auth_token,
            astrovox_tauri::auth::logout,
            astrovox_tauri::deep_link::handle_deep_link,
            astrovox_tauri::deep_link::get_pending_deep_link,
            astrovox_tauri::deep_link::clear_pending_deep_link,
            astrovox_tauri::deep_link::open_deep_link
        ])
        .setup(|app| {
            setup_system_tray(app)?;
            setup_chat_window(app)?;

            let _ = check_for_updates(app);

            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(86400));
                loop {
                    interval.tick().await;
                    let _ = check_for_updates(&app_handle).await;
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
