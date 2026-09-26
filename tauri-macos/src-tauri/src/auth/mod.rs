use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthState {
    pub access_token: String,
    pub refresh_token: String,
    pub expires_at: i64,
    pub user_id: String,
    pub email: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignupRequest {
    pub email: String,
    pub password: String,
    pub full_name: String,
}

#[tauri::command]
pub async fn authenticate(app: AppHandle, request: LoginRequest) -> Result<AuthState, String> {
    let client = reqwest::Client::new();
    let settings = app.state::<crate::settings::SettingsManager>();
    let settings = settings.lock().map_err(|e| e.to_string())?;
    let api_base = settings.api_base.clone();
    drop(settings);

    let response = client
        .post(format!("{}/v1/auth/login", api_base))
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Login failed: {}", e))?;

    if !response.status().is_success() {
        let error_text = response.text().await.unwrap_or_default();
        return Err(format!("Login failed: {}", error_text));
    }

    let result: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;
    let auth_state = AuthState {
        access_token: result["access_token"].as_str().unwrap_or("").to_string(),
        refresh_token: result["refresh_token"].as_str().unwrap_or("").to_string(),
        expires_at: chrono::Utc::now().timestamp() + (result["expires_in"].as_u64().unwrap_or(3600) as i64),
        user_id: result["user"]["id"].as_str().unwrap_or("").to_string(),
        email: result["user"]["email"].as_str().unwrap_or("").to_string(),
    };

    Ok(auth_state)
}

#[tauri::command]
pub async fn signup(app: AppHandle, request: SignupRequest) -> Result<AuthState, String> {
    let client = reqwest::Client::new();
    let settings = app.state::<crate::settings::SettingsManager>();
    let settings = settings.lock().map_err(|e| e.to_string())?;
    let api_base = settings.api_base.clone();
    drop(settings);

    let response = client
        .post(format!("{}/v1/auth/register", api_base))
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Signup failed: {}", e))?;

    if !response.status().is_success() {
        let error_text = response.text().await.unwrap_or_default();
        return Err(format!("Signup failed: {}", error_text));
    }

    let result: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;
    let auth_state = AuthState {
        access_token: result["access_token"].as_str().unwrap_or("").to_string(),
        refresh_token: result["refresh_token"].as_str().unwrap_or("").to_string(),
        expires_at: chrono::Utc::now().timestamp() + (result["expires_in"].as_u64().unwrap_or(3600) as i64),
        user_id: result["user"]["id"].as_str().unwrap_or("").to_string(),
        email: result["user"]["email"].as_str().unwrap_or("").to_string(),
    };

    Ok(auth_state)
}

#[tauri::command]
pub async fn refresh_auth_token(app: AppHandle) -> Result<AuthState, String> {
    let client = reqwest::Client::new();
    let settings = app.state::<crate::settings::SettingsManager>();
    let settings = settings.lock().map_err(|e| e.to_string())?;
    let api_base = settings.api_base.clone();
    drop(settings);

    let response = client
        .post(format!("{}/v1/auth/refresh", api_base))
        .json(&serde_json::json!({"refresh_token": ""}))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if !response.status().is_success() {
        return Err("Token refresh failed".to_string());
    }

    let result: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;
    Ok(AuthState {
        access_token: result["access_token"].as_str().unwrap_or("").to_string(),
        refresh_token: result["refresh_token"].as_str().unwrap_or("").to_string(),
        expires_at: chrono::Utc::now().timestamp() + (result["expires_in"].as_u64().unwrap_or(3600) as i64),
        user_id: result["user"]["id"].as_str().unwrap_or("").to_string(),
        email: result["user"]["email"].as_str().unwrap_or("").to_string(),
    })
}

#[tauri::command]
pub async fn logout(app: AppHandle) -> Result<(), String> {
    let settings = app.state::<crate::settings::SettingsManager>();
    let mut settings = settings.lock().map_err(|e| e.to_string())?;
    settings.api_key = String::new();
    Ok(())
}
