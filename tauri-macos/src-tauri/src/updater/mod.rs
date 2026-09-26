use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub version: String,
    pub changelog: Option<String>,
    pub download_url: Option<String>,
    pub published_at: Option<String>,
    pub min_supported_version: Option<String>,
    pub is_critical: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateProgress {
    pub stage: String,
    pub progress: f64,
    pub message: String,
}

static LAST_UPDATE_CHECK: Mutex<i64> = Mutex::new(0);

#[tauri::command]
pub async fn check_updates(app: AppHandle) -> Result<Option<UpdateInfo>, String> {
    let settings = app.state::<crate::settings::SettingsManager>();
    let settings = settings.lock().map_err(|e| e.to_string())?;

    let now = chrono::Utc::now().timestamp();
    let last_check = *LAST_UPDATE_CHECK.lock().map_err(|e| e.to_string())?;

    if now - last_check < (settings.update_check_interval_hours as i64 * 3600) && !settings.auto_update {
        return Ok(None);
    }

    let api_key = settings.api_key.clone();
    drop(settings);

    if api_key.is_empty() {
        return Ok(None);
    }

    let _ = app.emit("update-check-started", ());

    let result = check_remote_updates(&app, &api_key).await;

    match &result {
        Ok(Some(update)) => {
            let _ = app.emit("update-available", update);
        }
        Ok(None) => {
            let _ = app.emit("update-not-available", ());
        }
        Err(e) => {
            let _ = app.emit("update-check-failed", e);
        }
    }

    result
}

#[tauri::command]
pub async fn install_update(app: AppHandle, update: UpdateInfo) -> Result<(), String> {
    if let Some(download_url) = &update.download_url {
        let _ = app.emit("update-progress", UpdateProgress {
            stage: "downloading".to_string(),
            progress: 0.0,
            message: format!("Downloading v{}...", update.version),
        });

        let client = reqwest::Client::new();
        let response = client.get(download_url).send().await.map_err(|e| e.to_string())?;

        let app_data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
        let installer_path = app_data_dir.join(format!("astrovox-setup-{}.exe", update.version));
        let mut file = std::fs::File::create(&installer_path).map_err(|e| e.to_string())?;
        let mut bytes_written = 0u64;

        let total_size = response.content_length().unwrap_or(0);
        let mut stream = response.bytes_stream();

        while let Some(chunk) = stream.next().await {
            let chunk = chunk.map_err(|e| e.to_string())?;
            std::io::copy(&mut chunk.as_ref(), &mut file).map_err(|e| e.to_string())?;
            bytes_written += chunk.len() as u64;

            if let Some(total) = total_size {
                let progress = (bytes_written as f64 / total as f64) * 50.0;
                let _ = app.emit("update-progress", UpdateProgress {
                    stage: "downloading".to_string(),
                    progress,
                    message: format!("Downloaded {}/{}", bytes_written, total),
                });
            }
        }

        let _ = app.emit("update-progress", UpdateProgress {
            stage: "installing".to_string(),
            progress: 75.0,
            message: "Installing update...".to_string(),
        });

        if cfg!(target_os = "windows") {
            let _ = std::process::Command::new(&installer_path)
                .args(&["/S"])
                .spawn();
        }

        let _ = app.emit("update-complete", ());
    }

    Ok(())
}

async fn check_remote_updates(app: &AppHandle, api_key: &str) -> Result<Option<UpdateInfo>, String> {
    let settings = app.state::<crate::settings::SettingsManager>();
    let settings = settings.lock().map_err(|e| e.to_string())?;

    let client = reqwest::Client::new();
    let request = reqwest::Request::new(
        reqwest::Method::GET,
        format!("{}/v1/extensions/tauri/latest", settings.api_base),
    );

    let response = client
        .execute(request)
        .await
        .map_err(|e| format!("Update check failed: {}", e))?;

    if !response.status().is_success() {
        return Ok(None);
    }

    let data: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;

    if let (Some(version), Some(min_version)) = (
        data.get("version").and_then(|v| v.as_str()),
        data.get("min_supported_version").and_then(|v| v.as_str()),
    ) {
        if !is_version_newer(version, min_version) {
            return Ok(None);
        }

        let update = UpdateInfo {
            version: version.to_string(),
            changelog: data.get("changelog").and_then(|v| v.as_str()).map(String::from),
            download_url: data.get("download_url").and_then(|v| v.as_str()).map(String::from),
            published_at: data.get("published_at").and_then(|v| v.as_str()).map(String::from),
            min_supported_version: Some(min_version.to_string()),
            is_critical: data.get("is_critical").and_then(|v| v.as_bool()).unwrap_or(false),
        };

        *LAST_UPDATE_CHECK.lock().map_err(|e| e.to_string())? = chrono::Utc::now().timestamp();

        return Ok(Some(update));
    }

    Ok(None)
}

pub async fn check_for_updates(app: &AppHandle) -> Result<(), String> {
    let _ = check_updates(app.handle().clone()).await;
    Ok(())
}

fn is_version_newer(remote: &str, local: &str) -> bool {
    if remote == local {
        return false;
    }
    let normalize = |v: &str| {
        v.split('.')
            .filter_map(|s| s.parse::<u32>().ok())
            .collect::<Vec<_>>()
    };
    let remote_parts = normalize(remote);
    let local_parts = normalize(local);

    for i in 0..std::cmp::max(remote_parts.len(), local_parts.len()) {
        let r = remote_parts.get(i).copied().unwrap_or(0);
        let l = local_parts.get(i).copied().unwrap_or(0);
        match r.cmp(&l) {
            std::cmp::Ordering::Greater => return true,
            std::cmp::Ordering::Less => return false,
            std::cmp::Ordering::Equal => continue,
        }
    }
    false
}
