use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
    pub timestamp: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conversation {
    pub id: String,
    pub title: String,
    pub messages: Vec<Message>,
    pub model: String,
    pub created_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendMessageRequest {
    pub conversation_id: String,
    pub message: String,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendMessageResponse {
    pub ai_message: Message,
}

pub struct AstrovoxClient {
    api_key: String,
    base_url: String,
    client: reqwest::Client,
}

impl AstrovoxClient {
    pub fn new(api_key: &str, base_url: Option<&str>) -> Self {
        let base = base_url.unwrap_or("https://api.astrovox.ai/v1");
        Self {
            api_key: api_key.to_string(),
            base_url: base.trim_end_matches('/').to_string(),
            client: reqwest::Client::new(),
        }
    }

    pub async fn send_message(
        &self,
        conversation_id: &str,
        message: &str,
        model: &str,
    ) -> Result<SendMessageResponse, Box<dyn std::error::Error>> {
        let payload = SendMessageRequest {
            conversation_id: conversation_id.to_string(),
            message: message.to_string(),
            model: model.to_string(),
        };
        let resp = self
            .client
            .post(format!("{}/chat/message", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await?;
        let data: SendMessageResponse = resp.json().await?;
        Ok(data)
    }

    pub async fn create_conversation(
        &self,
        title: &str,
        model: &str,
    ) -> Result<Conversation, Box<dyn std::error::Error>> {
        let payload = HashMap::from([
            ("title", serde_json::json!(title)),
            ("model", serde_json::json!(model)),
        ]);
        let resp = self
            .client
            .post(format!("{}/conversations", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await?;
        let conv: Conversation = resp.json().await?;
        Ok(conv)
    }

    pub async fn list_conversations(&self) -> Result<Vec<Conversation>, Box<dyn std::error::Error>> {
        let resp = self
            .client
            .get(format!("{}/conversations", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .send()
            .await?;
        let convs: Vec<Conversation> = resp.json().await?;
        Ok(convs)
    }

    pub async fn health_check(&self) -> Result<HashMap<String, serde_json::Value>, Box<dyn std::error::Error>> {
        let resp = self
            .client
            .get(format!("{}/health", self.base_url))
            .send()
            .await?;
        let data: HashMap<String, serde_json::Value> = resp.json().await?;
        Ok(data)
    }
}
