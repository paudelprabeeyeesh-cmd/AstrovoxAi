"""Rust SDK client template."""
use reqwest::Client;
use serde_json::Value;

pub struct AstrovoxClient {
    pub base_url: String,
    pub api_key: String,
    pub client: Client,
}

impl AstrovoxClient {
    pub fn new(api_key: &str, base_url: Option<&str>) -> Self {
        let base = base_url.unwrap_or("https://api.astrovox.ai/v1").trim_end_matches('/');
        Self {
            base_url: base.to_string(),
            api_key: api_key.to_string(),
            client: Client::builder().timeout(std::time::Duration::from_secs(30)).build().unwrap(),
        }
    }

    pub async fn request(&self, method: &str, path: &str, body: Option<Value>) -> Result<Value, reqwest::Error> {
        let url = format!("{}{}", self.base_url, path);
        let mut req = self.client.request(method.parse().unwrap(), &url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json");
        if let Some(b) = body {
            req = req.json(&b);
        }
        let resp = req.send().await?;
        resp.json().await
    }

    pub async fn send_message(&self, conversation_id: &str, message: &str, model: &str) -> Result<Value, reqwest::Error> {
        let body = serde_json::json!({
            "conversation_id": conversation_id,
            "message": message,
            "model": model
        });
        self.request("POST", "/chat/message", Some(body)).await
    }

    pub async fn create_conversation(&self, title: &str, model: &str) -> Result<Value, reqwest::Error> {
        let body = serde_json::json!({
            "title": title,
            "model": model
        });
        self.request("POST", "/conversations", Some(body)).await
    }

    pub async fn list_conversations(&self) -> Result<Value, reqwest::Error> {
        self.request("GET", "/conversations", None).await
    }

    pub async fn health_check(&self) -> Result<Value, reqwest::Error> {
        self.request("GET", "/health", None).await
    }
}
