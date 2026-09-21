//! Memex SDK for Rust — local-first, zero-LLM agent memory.
//!
//! Usage:
//! ```no_run
//! use memex::MemexClient;
//!
//! let client = MemexClient::new("http://127.0.0.1:19420", None);
//! client.store("We decided to use JWT with 3600s expiry.").unwrap();
//! let result = client.recall("what did we decide about auth", 50).unwrap();
//! for m in &result.memories {
//!     println!("{}", m.text);
//! }
//! ```

use serde::{Deserialize, Serialize};
use std::time::Duration;

const DEFAULT_URL: &str = "http://127.0.0.1:19420";

#[derive(Debug, thiserror::Error)]
pub enum MemexError {
    #[error("HTTP error: {0}")]
    Http(String),
    #[error("Parse error: {0}")]
    Parse(String),
    #[error("Connection error: {0}")]
    Connection(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Memory {
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub score: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecallResult {
    pub memories: Vec<Memory>,
    pub method: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    pub count: i64,
    pub queued: Option<i64>,
    pub version: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoreResult {
    pub id: String,
    pub text: String,
}

pub struct MemexClient {
    base_url: String,
    api_token: Option<String>,
    agent: ureq::Agent,
}

impl MemexClient {
    pub fn new(base_url: &str, api_token: Option<String>) -> Self {
        let url = if base_url.is_empty() { DEFAULT_URL } else { base_url };
        Self {
            base_url: url.to_string(),
            api_token,
            agent: ureq::AgentBuilder::new()
                .timeout(Duration::from_secs(30))
                .build(),
        }
    }

    fn request(&self, method: &str, path: &str, body: Option<&str>) -> Result<String, MemexError> {
        let url = format!("{}{}", self.base_url, path);
        let mut req = self.agent.request(method, &url);
        req = req.set("Content-Type", "application/json");
        if let Some(ref token) = self.api_token {
            req = req.set("Authorization", &format!("Bearer {}", token));
        }
        let resp = if let Some(b) = body {
            req.send_string(b)
        } else {
            req.call()
        };
        match resp {
            Ok(r) => r.into_string().map_err(|e| MemexError::Http(e.to_string())),
            Err(ureq::Error::Status(code, resp)) => {
                let msg = resp.into_string().unwrap_or_default();
                Err(MemexError::Http(format!("HTTP {}: {}", code, msg)))
            }
            Err(e) => Err(MemexError::Connection(e.to_string())),
        }
    }

    pub fn health(&self) -> Result<HealthStatus, MemexError> {
        let body = self.request("GET", "/health", None)?;
        serde_json::from_str(&body).map_err(|e| MemexError::Parse(e.to_string()))
    }

    pub fn store(&self, text: &str) -> Result<StoreResult, MemexError> {
        let body = serde_json::json!({"text": text}).to_string();
        let resp = self.request("POST", "/store", Some(&body))?;
        serde_json::from_str(&resp).map_err(|e| MemexError::Parse(e.to_string()))
    }

    pub fn recall(&self, query: &str, limit: usize) -> Result<RecallResult, MemexError> {
        let body = serde_json::json!({"text": query, "limit": limit}).to_string();
        let resp = self.request("POST", "/recall", Some(&body))?;
        serde_json::from_str(&resp).map_err(|e| MemexError::Parse(e.to_string()))
    }

    pub fn query(&self, query: &str, limit: usize) -> Result<RecallResult, MemexError> {
        let body = serde_json::json!({"text": query, "limit": limit}).to_string();
        let resp = self.request("POST", "/query", Some(&body))?;
        serde_json::from_str(&resp).map_err(|e| MemexError::Parse(e.to_string()))
    }
}
