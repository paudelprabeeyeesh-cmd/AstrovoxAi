use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::AppHandle;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub api_key: String,
    pub api_base: String,
    pub model: String,
    pub max_tokens: u32,
    pub temperature: f64,
    pub auto_update: bool,
    pub update_check_interval_hours: u64,
    pub show_notifications: bool,
    pub theme: String,
    pub conversation_id: String,
    pub version: String,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            api_base: "https://api.astrovox.ai".to_string(),
            model: "gpt-4".to_string(),
            max_tokens: 2048,
            temperature: 0.7,
            auto_update: true,
            update_check_interval_hours: 24,
            show_notifications: true,
            theme: "dark".to_string(),
            conversation_id: format!("tauri-{}", chrono::Utc::now().timestamp()),
            version: "1.1.0".to_string(),
        }
    }
}

pub struct SettingsManager {
    pub settings: Mutex<AppSettings>,
}

impl SettingsManager {
    pub fn new() -> Self {
        Self {
            settings: Mutex::new(AppSettings::default()),
        }
    }

    pub fn load(&self, app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
        let app_data_dir = app.path().app_data_dir()?;
        std::fs::create_dir_all(&app_data_dir)?;
        let settings_path = app_data_dir.join("settings.json");

        if settings_path.exists() {
            let content = std::fs::read_to_string(settings_path)?;
            let loaded: AppSettings = serde_json::from_str(&content)?;
            let mut settings = self.settings.lock().map_err(|e| e.to_string())?;
            *settings = loaded;
        }

        Ok(())
    }

    pub fn save(&self, app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
        let settings = self.settings.lock().map_err(|e| e.to_string())?;
        let app_data_dir = app.path().app_data_dir()?;
        std::fs::create_dir_all(&app_data_dir)?;
        let settings_path = app_data_dir.join("settings.json");
        let json = serde_json::to_string_pretty(&*settings)?;
        std::fs::write(settings_path, json)?;
        Ok(())
    }

    pub fn get(&self) -> Result<AppSettings, Box<dyn std::error::Error>> {
        let settings = self.settings.lock().map_err(|e| e.to_string())?;
        Ok(settings.clone())
    }

    pub fn update<F>(&self, f: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnOnce(&mut AppSettings),
    {
        let mut settings = self.settings.lock().map_err(|e| e.to_string())?;
        f(&mut settings);
        Ok(())
    }
}

#[tauri::command]
pub async fn get_settings(app: AppHandle) -> Result<AppSettings, String> {
    let manager = app.state::<SettingsManager>();
    manager.get().map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn save_settings(app: AppHandle, new_settings: AppSettings) -> Result<(), String> {
    let manager = app.state::<SettingsManager>();
    manager.update(|s| {
        s.api_key = new_settings.api_key;
        s.api_base = new_settings.api_base;
        s.model = new_settings.model;
        s.max_tokens = new_settings.max_tokens;
        s.temperature = new_settings.temperature;
        s.auto_update = new_settings.auto_update;
        s.show_notifications = new_settings.show_notifications;
    }).map_err(|e| e.to_string())?;
    manager.save(&app).map_err(|e| e.to_string())
}
