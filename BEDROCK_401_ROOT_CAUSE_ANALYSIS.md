# Root Cause Analysis: 401 Unauthorized Errors in Codex Instances

## Executive Summary

All 74 codex instances spawned by the supervisor failed with **401 Unauthorized errors** during the GCP security assessment. The root cause has been identified: **The Rust-based Codex CLI has no AWS Bedrock support**, while the Python supervisor successfully uses Bedrock.

## Problem Statement

- **Supervisor (Python)**: Successfully authenticates with AWS Bedrock ✅
- **Codex Instances (Rust CLI)**: All fail with 401 Unauthorized ❌  
- **Failure Rate**: 100% (74/74 instances)
- **Bearer Token Status**: Valid and working (tested)

## Root Cause

### The Mismatch

1. **Supervisor Side (Python)**
   - Uses supervisor/llm_client.py with boto3
   - Reads AWS_BEARER_TOKEN_BEDROCK from environment
   - Calls https://bedrock-runtime.us-west-2.amazonaws.com
   - **Works perfectly** - All HTTP 200 responses

2. **Codex Instance Side (Rust)**
   - Uses built-in model providers from codex-rs/core/src/model_provider_info.rs
   - **Only supports**: openai and oss (local models)
   - **No Bedrock support exists in the Rust codebase**
   - Defaults to OpenAI provider
   - Tries to authenticate with OpenAI API
   - **Fails with 401** because it's using wrong API endpoint

## Verification

### Test 1: Bearer Token Validity
✅ SUCCESS: Bearer token is VALID
Status Code: 200

### Test 2: Supervisor Can Use Bedrock
Supervisor makes hundreds of successful Bedrock API calls (HTTP 200).

### Test 3: All Codex Instances Fail
Pattern repeats for all 74 instances - 401 Unauthorized.

## Solutions

### Option 1: Add Bedrock Support to Codex Rust CLI (Recommended)

**Pros**:
- Proper architecture
- Reusable for all Codex CLI users
- No ongoing costs

**Cons**:
- Significant Rust development work (2-4 hours)

### Option 2: Use OpenRouter as Bridge (Quick Fix)

Configure Codex CLI to use OpenRouter, which supports routing to Bedrock models.

**Pros**:
- Works immediately (5 minutes)
- No code changes

**Cons**:
- Requires OpenRouter API key
- Additional cost

### Option 3: Switch Supervisor to OpenAI

Both supervisor and codex use same OpenAI provider.

**Pros**:
- Works with existing code

**Cons**:
- Loses Bedrock benefits

## Recommendation

**Implement Option 1: Add Bedrock Support to Codex Rust CLI**

**Immediate Workaround**: Use Option 2 (OpenRouter) while developing Option 1.

## Conclusion

The 401 errors were **not authentication failures** - the bearer token is valid. The failure occurred because the **Codex Rust CLI lacks AWS Bedrock support** and falls back to calling OpenAI's API with Bedrock-formatted model IDs, which OpenAI rejects.

This is a **missing feature**, not a bug. The supervisor and codex CLI use different LLM client implementations (Python vs Rust), and only the Python side supports Bedrock.

---
*Analysis Date: January 29, 2026*
*Analyst: Claude Sonnet 4.5*
