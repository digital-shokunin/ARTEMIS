# Bedrock Support Workaround Guide

## What Was Fixed

### 1. ✅ Error Surfacing (Implemented)

**Problem**: Supervisor reported instances as "completed successfully" even when they hit 401 errors.

**Solution**: Modified `supervisor/orchestration/instance_manager.py` to:
- Check instance output files (`realtime_context.txt`, `final_result.json`) for error patterns
- Detect 401 Unauthorized, 403 Forbidden, and other HTTP errors
- Mark instances as "failed" and log specific error details even if exit code is 0

**Impact**: Supervisor will now properly surface 401 errors in logs:
```
❌ Instance gcp-iam-recon reported success but contains errors:
❌ 401 Unauthorized - Authentication failed: exceeded retry limit, last status: 401 Unauthorized
```

### 2. 🚧 Bedrock Support (Requires More Work)

**Problem**: Codex Rust CLI has no AWS Bedrock support.

**Immediate Workaround**: Use OpenRouter as a bridge (see below)

**Proper Solution**: Implement Bedrock in Rust CLI (2-4 hours, see implementation plan below)

---

## Quick Fix: Use OpenRouter (5 Minutes)

OpenRouter supports routing to AWS Bedrock models and works with existing Codex CLI.

### Step 1: Get OpenRouter API Key

1. Go to https://openrouter.ai/
2. Sign up / log in
3. Navigate to Keys section
4. Create a new API key

### Step 2: Configure OpenRouter

Add to `/home/digish0/ARTEMIS/.env`:
```bash
# OpenRouter Configuration (for codex instances)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Subagent model (use OpenRouter format)
SUBAGENT_MODEL=anthropic/claude-opus-4-5

# Keep Bedrock for supervisor (it works fine)
BEDROCK_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-5-20251101-v1:0
AWS_BEARER_TOKEN_BEDROCK=<your-token>
```

### Step 3: Configure Codex CLI

Create `~/.codex/config.toml`:
```toml
# Use OpenRouter as default provider
model_provider = "openrouter"

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
wire_api = "chat"

# Optional: Configure model preferences
# [profiles.default]
# model = "anthropic/claude-opus-4-5"
# model_provider = "openrouter"
```

### Step 4: Test

Run a simple test:
```bash
cd /home/digish0/ARTEMIS
. .env
export SUBAGENT_MODEL=anthropic/claude-opus-4-5

# Test codex directly
echo "Test workspace" > /tmp/test_task.txt
codex-rs/target/release/codex exec --model anthropic/claude-opus-4-5 "Echo hello world"
```

### Step 5: Restart Supervisor

The next supervisor session will use:
- Supervisor: Bedrock (Python) ✅
- Codex Instances: OpenRouter (Rust) ✅

### Costs

OpenRouter adds ~20-30% markup on model costs:
- Claude Opus 4.5: $5.50 input / $27.50 output per MTok (vs Bedrock's $5/$25)
- Still cheaper than having the assessment fail completely!

---

## Proper Fix: Implement Bedrock Support (2-4 Hours)

For when you want native Bedrock support in Codex Rust CLI:

### Implementation Plan

#### Phase 1: Add Bedrock Wire API (30 min)

1. **Add enum variant** (`codex-rs/core/src/model_provider_info.rs:33`):
   ```rust
   pub enum WireApi {
       Responses,
       Chat,
       Bedrock,  // ← Add this
   }
   ```

2. **Add Bedrock provider** (`codex-rs/core/src/model_provider_info.rs:237`):
   ```rust
   pub fn built_in_model_providers() -> HashMap<String, ModelProviderInfo> {
       [
           ("openai", /* ... */),
           ("bedrock", P {
               name: "AWS Bedrock".into(),
               base_url: None,  // Constructed dynamically per region
               env_key: Some("AWS_BEARER_TOKEN_BEDROCK".into()),
               env_key_instructions: Some(
                   "Get bearer token from AWS IAM or use AWS SSO".into()
               ),
               wire_api: WireApi::Bedrock,
               query_params: None,
               http_headers: None,
               env_http_headers: Some([
                   ("Authorization".to_string(), "AWS_BEARER_TOKEN_BEDROCK".to_string()),
               ].into_iter().collect()),
               request_max_retries: Some(3),
               stream_max_retries: Some(5),
               stream_idle_timeout_ms: Some(300_000),
               requires_openai_auth: false,
           }),
           (BUILT_IN_OSS_MODEL_PROVIDER_ID, create_oss_provider()),
       ]
       // ...
   }
   ```

3. **Add region/endpoint handling**:
   - Read `BEDROCK_REGION` env var (default: us-west-2)
   - Construct endpoint: `https://bedrock-runtime.{region}.amazonaws.com`

#### Phase 2: Implement Bedrock Converse API (60-90 min)

1. **Create Bedrock request types** (`codex-rs/core/src/bedrock_api.rs` - new file):
   ```rust
   #[derive(Serialize)]
   pub struct BedrockConverseRequest {
       #[serde(rename = "inferenceConfig")]
       pub inference_config: InferenceConfig,
       pub messages: Vec<BedrockMessage>,
       #[serde(skip_serializing_if = "Option::is_none")]
       pub system: Option<Vec<SystemContent>>,
       // ... other fields
   }

   #[derive(Deserialize)]
   pub struct BedrockConverseResponse {
       pub output: BedrockOutput,
       pub usage: BedrockUsage,
       #[serde(rename = "stopReason")]
       pub stop_reason: String,
       // ...
   }
   ```

2. **Implement request conversion**:
   - Convert Codex's internal format → Bedrock Converse format
   - Handle tools (Bedrock uses different tool format)

3. **Implement response parsing**:
   - Parse Bedrock response → Codex internal format
   - Handle streaming responses

#### Phase 3: Bearer Token Authentication (30 min)

1. **Modify client.rs** to handle bearer tokens:
   ```rust
   // In build_request() method
   if provider.wire_api == WireApi::Bedrock {
       if let Some(env_key) = &provider.env_key {
           if let Ok(token) = std::env::var(env_key) {
               req_builder = req_builder.bearer_auth(token);
           }
       }
   }
   ```

2. **Handle authorization header**:
   - Format: `Authorization: Bearer <token>`
   - Add to all Bedrock requests

#### Phase 4: Testing (30-60 min)

1. **Unit tests**:
   - Test Bedrock request serialization
   - Test Bedrock response parsing
   - Test bearer token handling

2. **Integration tests**:
   - Spawn single codex instance with Bedrock
   - Verify successful authentication
   - Verify model responses

3. **Full supervisor test**:
   - Run supervisor with Bedrock-enabled codex
   - Spawn multiple instances
   - Verify no 401 errors

#### Files to Modify

1. `codex-rs/core/src/model_provider_info.rs` - Add Bedrock provider
2. `codex-rs/core/src/bedrock_api.rs` - New file for Bedrock types
3. `codex-rs/core/src/client.rs` - Add Bedrock request handling
4. `codex-rs/core/src/lib.rs` - Export bedrock_api module
5. `codex-rs/Cargo.toml` - May need additional dependencies

### Reference Implementation

The Python supervisor already has a working Bedrock implementation in `supervisor/llm_client.py` (lines 126-229). Use this as a reference for:
- Request format
- Response parsing
- Error handling
- Bearer token usage

### Testing Checklist

- [ ] Bearer token read from env
- [ ] Correct endpoint constructed with region
- [ ] Authorization header added
- [ ] Request format matches Bedrock Converse API
- [ ] Response parsed correctly
- [ ] Streaming works
- [ ] Tools/function calling works
- [ ] Error messages are clear
- [ ] Multiple concurrent instances work
- [ ] Supervisor + Codex integration works

---

## Recommendation

**For immediate testing**: Use OpenRouter workaround (5 min setup)

**For production**: Implement native Bedrock support (2-4 hours development)

The error surfacing fix is already implemented and will help debug issues with either approach!

---

*Guide Created: January 29, 2026*
*Last Updated: January 29, 2026*
