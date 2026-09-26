use tauri::{AppHandle, Manager, WebviewWindow, Window};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
    pub timestamp: String,
    pub id: Option<String>,
    pub offline: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatRequest {
    pub message: String,
    pub conversation_id: Option<String>,
    pub model: Option<String>,
    pub stream: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    pub ai_message: Option<ChatMessage>,
    pub content: Option<String>,
    pub conversation_id: Option<String>,
}

static CONVERSATIONS: Mutex<std::collections::HashMap<String, Vec<ChatMessage>>> =
    Mutex::new(std::collections::HashMap::new());

#[tauri::command]
pub async fn send_message(
    app: AppHandle,
    window: WebviewWindow,
    request: ChatRequest,
) -> Result<ChatResponse, String> {
    let api_key = get_api_key(&app).await?;
    let conversation_id = request
        .conversation_id
        .unwrap_or_else(|| format!("tauri-{}", chrono::Utc::now().timestamp()));

    let user_message = ChatMessage {
        role: "user".to_string(),
        content: request.message.clone(),
        timestamp: chrono::Utc::now().to_rfc3339(),
        id: Some(format!("msg-{}", chrono::Utc::now().timestamp_millis())),
        offline: false,
    };

    let mut conversations = CONVERSATIONS.lock().map_err(|e| e.to_string())?;
    conversations
        .entry(conversation_id.clone())
        .or_default()
        .push(user_message.clone());

    let api_base = get_api_base(&app);
    let client = reqwest::Client::new();

    let body = serde_json::json!({
        "conversation_id": conversation_id,
        "message": request.message,
        "model": request.model.unwrap_or_else(|| "gpt-4".to_string()),
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": request.stream.unwrap_or(false)
    });

    let response = client
        .post(format!("{}/v1/chat/message", api_base))
        .header("Content-Type", "application/json")
        .header("Authorization", format!("Bearer {}", api_key))
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !response.status().is_success() {
        let error_text = response.text().await.unwrap_or_default();
        return Err(format!("API error: {}", error_text));
    }

    let result: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;
    let ai_content = result["ai_message"]["content"]
        .as_str()
        .or_else(|| result["content"].as_str())
        .unwrap_or("No response")
        .to_string();

    let ai_message = ChatMessage {
        role: "assistant".to_string(),
        content: ai_content.clone(),
        timestamp: chrono::Utc::now().to_rfc3339(),
        id: Some(format!("msg-{}", chrono::Utc::now().timestamp_millis())),
        offline: false,
    };

    conversations
        .entry(conversation_id.clone())
        .or_default()
        .push(ai_message.clone());

    drop(conversations);

    window
        .emit("chat-message", &ai_message)
        .map_err(|e| e.to_string())?;

    Ok(ChatResponse {
        ai_message: Some(ai_message),
        content: Some(ai_content),
        conversation_id: Some(conversation_id),
    })
}

#[tauri::command]
pub async fn get_conversation(conversation_id: String) -> Result<Vec<ChatMessage>, String> {
    let conversations = CONVERSATIONS.lock().map_err(|e| e.to_string())?;
    Ok(conversations
        .get(&conversation_id)
        .cloned()
        .unwrap_or_default())
}

#[tauri::command]
pub async fn clear_conversation(conversation_id: String) -> Result<(), String> {
    let mut conversations = CONVERSATIONS.lock().map_err(|e| e.to_string())?;
    conversations.remove(&conversation_id);
    Ok(())
}

#[tauri::command]
pub async fn clear_all_conversations() -> Result<(), String> {
    let mut conversations = CONVERSATIONS.lock().map_err(|e| e.to_string())?;
    conversations.clear();
    Ok(())
}

async fn get_api_key(app: &AppHandle) -> Result<String, String> {
    let settings = app.state::<crate::settings::AppSettings>();
    let settings = settings.lock().map_err(|e| e.to_string())?;
    if settings.api_key.is_empty() {
        return Err("API key not configured".to_string());
    }
    Ok(settings.api_key.clone())
}

fn get_api_base(app: &AppHandle) -> String {
    let settings = app.state::<crate::settings::AppSettings>();
    if let Ok(settings) = settings.lock() {
        return settings.api_base.clone();
    }
    "https://api.astrovox.ai".to_string()
}
