use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::AppHandle;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeepLinkResult {
    pub route: String,
    pub conversation_id: Option<String>,
    pub access_token: Option<String>,
    pub refresh_token: Option<String>,
    pub params: std::collections::HashMap<String, String>,
}

static PENDING_DEEP_LINK: Mutex<Option<DeepLinkResult>> = Mutex::new(None);

const ROUTE_MAP: &[(&str, &str)] = &[
    ("/chat", "chat"),
    ("/memory", "memory"),
    ("/settings", "settings"),
    ("/dashboard", "chat"),
    ("/conversation", "conversation"),
    ("/reset-password", "reset-password"),
];

#[tauri::command]
pub async fn handle_deep_link(url: String) -> Result<DeepLinkResult, String> {
    let result = parse_deep_link(&url)?;

    let mut pending = PENDING_DEEP_LINK.lock().map_err(|e| e.to_string())?;
    *pending = Some(result.clone());

    Ok(result)
}

#[tauri::command]
pub async fn get_pending_deep_link() -> Result<Option<DeepLinkResult>, String> {
    let pending = PENDING_DEEP_LINK.lock().map_err(|e| e.to_string())?;
    Ok(pending.clone())
}

#[tauri::command]
pub async fn clear_pending_deep_link() -> Result<(), String> {
    let mut pending = PENDING_DEEP_LINK.lock().map_err(|e| e.to_string())?;
    *pending = None;
    Ok(())
}

#[tauri::command]
pub fn generate_deep_link(route: &str, params: std::collections::HashMap<String, String>) -> String {
    let base_url = "https://astrovox.ai";

    let mut url = format!("{}{}", base_url, route);
    if !params.is_empty() {
        let query_parts: Vec<String> = params
            .iter()
            .filter(|(_, v)| !v.is_empty())
            .map(|(k, v)| format!("{}={}", urlencoding::encode(k), urlencoding::encode(v)))
            .collect();
        if !query_parts.is_empty() {
            url.push('?');
            url.push_str(&query_parts.join("&"));
        }
    }
    url
}

#[tauri::command]
pub async fn open_deep_link(app: AppHandle, route: &str, params: std::collections::HashMap<String, String>) -> Result<(), String> {
    let url = generate_deep_link(route, params);

    if let Err(e) = open::that(&url) {
        return Err(format!("Failed to open deep link: {}", e));
    }

    Ok(())
}

fn parse_deep_link(url: &str) -> Result<DeepLinkResult, String> {
    let parsed = url::Url::parse(url).map_err(|e| format!("Invalid URL: {}", e))?;
    let path = parsed.path();
    let query_params: std::collections::HashMap<String, String> = parsed
        .query_pairs()
        .filter_map(|(k, v)| {
            if k.is_empty() {
                None
            } else {
                Some((k.into_owned(), v.into_owned()))
            }
        })
        .collect();

    let mut route = "chat";
    for (path_pattern, route_name) in ROUTE_MAP.iter() {
        if path == *path_pattern {
            route = route_name;
            break;
        }
    }

    let mut result = DeepLinkResult {
        route: route.to_string(),
        conversation_id: None,
        access_token: None,
        refresh_token: None,
        params: query_params.clone(),
    };

    match route {
        "conversation" => {
            result.conversation_id = query_params.get("id").cloned();
        }
        "reset-password" => {
            result.access_token = query_params.get("access_token").cloned();
            result.refresh_token = query_params.get("refresh_token").cloned();
        }
        _ => {}
    }

    let mut pending = PENDING_DEEP_LINK.lock().map_err(|e| e.to_string())?;
    *pending = Some(result.clone());

    Ok(result)
}

pub fn register_deep_link_handler() {
    println!("Deep link handler registered");
}
