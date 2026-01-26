# ARTEMIS Architecture Overview

## What is ARTEMIS?

**ARTEMIS** (Automated Red Teaming Engine with Multi-agent Intelligent Supervision) is an autonomous agent system designed to automate vulnerability discovery and CTF (Capture The Flag) challenges. It uses a supervisor-agent architecture where a high-level supervisor coordinates multiple specialized sub-agents (Codex instances) to accomplish complex security tasks.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       SUPERVISOR                             │
│  (High-level reasoning, task planning, coordination)        │
│  - Analyzes challenges and objectives                       │
│  - Spawns and manages Codex instances                       │
│  - Tracks progress and makes decisions                      │
│  - Uses Claude Opus 4.5 or other frontier models           │
└────────────┬────────────────────────────────────────────────┘
             │
             │ spawns & coordinates
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    CODEX INSTANCES                          │
│  (Specialized execution agents)                             │
│  - Execute specific tasks assigned by supervisor            │
│  - Run commands, analyze files, exploit vulnerabilities     │
│  - Report results back to supervisor                        │
│  - Multiple instances can run concurrently                  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Supervisor (`supervisor/`)

The supervisor is the brain of ARTEMIS. It:

- **Receives objectives** from configuration files (challenges, tasks)
- **Makes high-level decisions** about strategy and approach
- **Spawns Codex instances** to execute specific tasks
- **Monitors progress** by reading instance logs
- **Adapts strategy** based on results from sub-agents
- **Manages conversation history** and context with the LLM
- **Handles tool calls** for actions like spawning agents, searching, etc.

**Key Files:**
- `supervisor/supervisor.py` - Main entry point
- `supervisor/orchestration/orchestrator.py` - Core orchestration logic
- `supervisor/llm_client.py` - LLM API integration (OpenAI, Bedrock, OpenRouter)
- `supervisor/tools/` - Tool implementations (spawn_codex, web_search, etc.)

### 2. Codex Instances (`codex-rs/`)

Codex is a Rust-based autonomous coding agent (forked from OpenAI's Codex) that:

- **Executes specific tasks** assigned by the supervisor
- **Runs shell commands** in sandboxed environments
- **Analyzes files and code** to find vulnerabilities or flags
- **Uses specialized prompts** based on task type (via routing)
- **Reports results** back to the supervisor via logs

**Key Aspects:**
- Written in Rust for performance and safety
- Can run multiple instances concurrently
- Each instance has isolated workspace and logging
- Supports different "specialists" (linux-privesc, web-exploit, etc.)

### 3. LLM Client (`supervisor/llm_client.py`)

A unified client that supports multiple LLM providers:

**Supported Providers:**
- **OpenAI** - Direct OpenAI API
- **OpenRouter** - Multi-model API aggregator
- **Amazon Bedrock** - AWS-hosted models with two APIs:
  - Messages API (for Anthropic Claude models)
  - Converse API (for non-Anthropic models like Llama)

**Key Features:**
- Automatic message format conversion between different APIs
- Tool call handling with proper result formatting
- Support for both AWS SDK and bearer token authentication
- Handles differences in API requirements (toolResult formatting, etc.)

### 4. Routing System (`supervisor/orchestration/routing.py`)

The router selects the appropriate specialist for each task:

**Available Specialists:**
- `linux-privesc` - Linux privilege escalation and system analysis
- `web-exploit` - Web application vulnerabilities
- `crypto` - Cryptographic challenges
- `forensics` - Digital forensics tasks
- `reversing` - Reverse engineering

The router analyzes task descriptions and selects the best specialist based on keywords and patterns.

### 5. Context Manager (`supervisor/orchestration/context_manager.py`)

Manages conversation history and token limits:

- **Tracks token usage** to stay within model limits (200K tokens for Claude Opus 4.5)
- **Summarizes old conversations** when approaching limits
- **Preserves recent context** for continuity
- **Balances detail vs. efficiency** in conversation history

### 6. Tools System (`supervisor/tools/`)

The supervisor has access to various tools:

- `spawn_codex` - Launch new Codex instances with specific tasks
- `read_instance_logs` - Read output from running/completed instances
- `kill_instance` - Terminate a running instance
- `web_search` - Search the internet for information
- `update_supervisor_todo` - Manage task tracking
- `finished` - Signal completion of the objective

## Execution Flow

### Standard Workflow

1. **Initialization**
   - Supervisor loads configuration (challenge description, objectives)
   - Initializes LLM client with configured model/provider
   - Sets up logging and working directory

2. **Triage (Optional)**
   - In non-benchmark mode, performs initial analysis
   - Decides if challenge is solvable
   - Plans initial approach

3. **Supervisor Loop**
   - **Iteration cycle:**
     1. Send conversation history to LLM
     2. LLM responds with text and/or tool calls
     3. Execute requested tools
     4. Append tool results to conversation history
     5. Repeat until objective is achieved or timeout

4. **Codex Execution**
   - Supervisor spawns Codex with specific task
   - Router selects appropriate specialist
   - Codex executes task autonomously
   - Results logged to instance-specific log file
   - Supervisor reads logs to understand results

5. **Completion**
   - Supervisor calls `finished` tool or makes benchmark submission
   - All instances terminated gracefully
   - Session logs saved for analysis

### Message Flow (Bedrock Converse Example)

When using non-Anthropic models via Bedrock Converse:

```
1. Supervisor → LLM: User message with task
2. LLM → Supervisor: Assistant message with toolUse blocks
3. Supervisor: Executes tools (e.g., spawn_codex)
4. Supervisor → LLM: User message with consolidated toolResult blocks
5. LLM → Supervisor: Assistant message with analysis/next steps
```

**Critical:** All tool results from a single assistant turn must be consolidated into ONE user message for Converse API compliance.

## Configuration System

### Config Files (`configs/`)

YAML files define:
- Challenge description and objectives
- Target files/directories
- Success criteria (flag patterns, submission format)
- Working hours constraints
- Timeout settings

**Example:**
```yaml
challenge:
  name: "it_has_begun"
  description: "Find the HTB{...} flag in the script"

objectives:
  - Find flag with pattern HTB{...}
  - Submit using submission tool

target:
  directory: "/home/user/ARTEMIS/test_files/it_has_begun"
```

### Environment Variables

Key environment variables:

**LLM Provider:**
- `LLM_PROVIDER` - openai, openrouter, or bedrock
- `OPENAI_API_KEY` / `OPENROUTER_API_KEY` - API keys
- `SUBAGENT_MODEL` - Model for Codex instances

**Bedrock (AWS):**
- `BEDROCK_REGION` - AWS region (e.g., us-east-2)
- `BEDROCK_MODEL_ID` - Model identifier
- `AWS_BEARER_TOKEN_BEDROCK` - Bearer token for runtime API

## Key Architectural Patterns

### 1. Supervisor-Agent Pattern

- **Supervisor** handles high-level reasoning and coordination
- **Agents** (Codex instances) handle specific execution tasks
- Clear separation between planning and execution
- Enables parallel task execution

### 2. Tool-Based Interaction

- LLM communicates via tool calls (structured function calls)
- Each tool has schema defining parameters
- Tool results returned as structured data
- Enables reliable, type-safe interactions

### 3. Multi-Provider LLM Support

- Unified client interface across providers
- Automatic message format conversion
- Provider-specific optimizations (token limits, API quirks)
- Easy to add new providers

### 4. Stateful Conversation Management

- Full conversation history maintained
- Automatic summarization when approaching limits
- Context preserved across iterations
- Enables complex multi-turn reasoning

## Benchmark Mode vs. Interactive Mode

### Benchmark Mode (`--benchmark-mode`)

- Skips triage process
- Runs for fixed duration
- Automatic submission detection
- Designed for CTF competition evaluation

### Interactive Mode (Default)

- Includes triage analysis
- Can run indefinitely
- Manual objective completion
- Suitable for real-world vulnerability discovery

## Logging and Debugging

### Log Structure

```
logs/
├── supervisor_session_<timestamp>/
│   ├── supervisor.log              # Supervisor decision log
│   ├── ctf-analysis-1.log          # Codex instance 1
│   ├── ctf-analysis-2.log          # Codex instance 2
│   └── ...
```

### Key Log Markers

- `🔄 Supervisor iteration N` - Start of iteration
- `🔧 Supervisor calling tool: <name>` - Tool execution
- `🚀 Spawned codex instance <id>` - New agent spawned
- `✅ Instance <id> completed successfully` - Agent finished
- `❌` - Errors and failures

## Common Workflows

### CTF Challenge Solving

1. Supervisor analyzes challenge description
2. Creates initial TODO list
3. Spawns Codex instance to explore target directory
4. Reads instance logs to understand findings
5. Spawns specialized instances for exploitation
6. Monitors progress and adapts strategy
7. Submits flag when found

### Vulnerability Discovery

1. Supervisor receives target system description
2. Routes task to appropriate specialist
3. Spawns reconnaissance instances
4. Analyzes results for potential vulnerabilities
5. Spawns exploitation instances
6. Validates findings
7. Reports vulnerabilities

## Extending ARTEMIS

### Adding New Specialists

1. Create prompt in `supervisor/orchestration/specialists/`
2. Add routing rules in `routing.py`
3. Test with specific task types

### Adding New Tools

1. Implement tool in `supervisor/tools/`
2. Register in `tool_manager.py`
3. Add to tool definitions with schema
4. Update supervisor prompts if needed

### Supporting New LLM Providers

1. Add provider detection in `llm_client.py`
2. Implement message format conversion
3. Handle provider-specific quirks
4. Test tool call handling

## Performance Considerations

### Token Management

- Claude Opus 4.5: 200K context window
- Summarization triggers at 185K tokens
- Recent context (20 messages) preserved
- Balances detail and efficiency

### Concurrent Execution

- Multiple Codex instances can run in parallel
- Supervisor polls for completion
- Logs provide async communication
- Scales with available compute resources

### API Rate Limits

- Different providers have different limits
- Bedrock: Varies by region and model
- OpenRouter: Depends on underlying model
- Consider delays between iterations if hitting limits

## Security Considerations

### Sandboxing

- Codex instances run with workspace restrictions
- Network access configurable
- File system access limited to workspace
- Process isolation between instances

### Credential Management

- API keys via environment variables
- Never commit credentials to git
- Use `.env` file (excluded from git)
- IAM roles preferred for AWS Bedrock

## Troubleshooting

### Common Issues

**"Expected toolResult blocks" error:**
- Fixed in recent update (consolidated tool results)
- Ensure using latest llm_client.py

**Empty responses from supervisor:**
- Check token limits
- Review conversation history length
- Verify API connectivity

**Codex instances hanging:**
- Check for infinite loops in prompts
- Verify sandbox configuration
- Review instance logs for errors

**Tool execution failures:**
- Verify environment configuration
- Check API credentials
- Review supervisor.log for details

## Additional Resources

- **Detailed Usage:** `docs/supervisor-usage.md`
- **Configuration Reference:** Example configs in `configs/`
- **API Documentation:** Provider-specific docs (OpenAI, Bedrock, etc.)
- **Source Code:** Inline documentation in Python/Rust files
