//! AWS Bedrock Converse API types and utilities.

use serde::{Deserialize, Serialize};

/// Bedrock Converse API request body.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BedrockConverseRequest {
    pub messages: Vec<BedrockMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub system: Option<Vec<SystemContentBlock>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub inference_config: Option<InferenceConfig>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_config: Option<ToolConfig>,
}

/// A message in the Bedrock conversation.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BedrockMessage {
    pub role: String,
    pub content: Vec<ContentBlock>,
}

/// Content block in a message.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "camelCase")]
pub enum ContentBlock {
    #[serde(rename = "text")]
    Text { text: String },
    #[serde(rename = "toolUse")]
    ToolUse {
        #[serde(rename = "toolUseId")]
        tool_use_id: String,
        name: String,
        input: serde_json::Value,
    },
    #[serde(rename = "toolResult")]
    ToolResult {
        #[serde(rename = "toolUseId")]
        tool_use_id: String,
        content: Vec<ToolResultContent>,
        #[serde(skip_serializing_if = "Option::is_none")]
        status: Option<String>,
    },
}

/// Tool result content.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ToolResultContent {
    Text { text: String },
}

/// System content block.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SystemContentBlock {
    pub text: String,
}

/// Inference configuration for the request.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InferenceConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_p: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stop_sequences: Option<Vec<String>>,
}

/// Tool configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolConfig {
    pub tools: Vec<Tool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_choice: Option<ToolChoice>,
}

/// Tool definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Tool {
    pub tool_spec: ToolSpec,
}

/// Tool specification.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolSpec {
    pub name: String,
    pub description: String,
    pub input_schema: InputSchema,
}

/// Input schema for a tool.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InputSchema {
    pub json: serde_json::Value,
}

/// Tool choice configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "camelCase")]
pub enum ToolChoice {
    #[serde(rename = "auto")]
    Auto {},
    #[serde(rename = "any")]
    Any {},
    #[serde(rename = "tool")]
    Tool { name: String },
}

/// Bedrock Converse API response.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BedrockConverseResponse {
    pub output: BedrockOutput,
    #[serde(rename = "stopReason")]
    pub stop_reason: String,
    pub usage: BedrockUsage,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metrics: Option<BedrockMetrics>,
}

/// Output from Bedrock response.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BedrockOutput {
    pub message: BedrockMessage,
}

/// Usage statistics from Bedrock.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BedrockUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub total_tokens: Option<u32>,
}

/// Metrics from Bedrock.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BedrockMetrics {
    #[serde(rename = "latencyMs")]
    pub latency_ms: u64,
}

impl BedrockConverseRequest {
    /// Create a new Bedrock Converse request with messages.
    pub fn new(messages: Vec<BedrockMessage>) -> Self {
        Self {
            messages,
            system: None,
            inference_config: None,
            tool_config: None,
        }
    }

    /// Set system messages.
    pub fn with_system(mut self, system: Vec<SystemContentBlock>) -> Self {
        self.system = Some(system);
        self
    }

    /// Set inference configuration.
    pub fn with_inference_config(mut self, config: InferenceConfig) -> Self {
        self.inference_config = Some(config);
        self
    }

    /// Set tool configuration.
    pub fn with_tool_config(mut self, config: ToolConfig) -> Self {
        self.tool_config = Some(config);
        self
    }
}

impl BedrockMessage {
    /// Create a new message with role and text content.
    pub fn new(role: impl Into<String>, text: impl Into<String>) -> Self {
        Self {
            role: role.into(),
            content: vec![ContentBlock::Text {
                text: text.into(),
            }],
        }
    }

    /// Create a new message with role and content blocks.
    pub fn with_content(role: impl Into<String>, content: Vec<ContentBlock>) -> Self {
        Self {
            role: role.into(),
            content,
        }
    }
}

impl ContentBlock {
    /// Create a text content block.
    pub fn text(text: impl Into<String>) -> Self {
        Self::Text {
            text: text.into(),
        }
    }

    /// Create a tool use content block.
    pub fn tool_use(tool_use_id: String, name: String, input: serde_json::Value) -> Self {
        Self::ToolUse {
            tool_use_id,
            name,
            input,
        }
    }

    /// Create a tool result content block.
    pub fn tool_result(tool_use_id: String, content: Vec<ToolResultContent>) -> Self {
        Self::ToolResult {
            tool_use_id,
            content,
            status: None,
        }
    }
}
