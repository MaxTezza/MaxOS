# MaxOS

[![CI](https://github.com/MaxTezza/MaxOS/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxTezza/MaxOS/actions/workflows/ci.yml)

Natural-language control plane for Linux that routes user intents to trusted autonomous agents. This repo contains the scaffolding, documentation, and first reference implementations for the MaxOS experiment described in the internal white papers.

## Why This Exists
- Treat the OS as a conversation: describe your goal once, let orchestrated agents execute the steps.
- Ship a privacy-conscious stack that can run fully offline with local LLMs but can burst to cloud APIs.
- Provide opinionated guidance (architecture, security, deployment) so additional agents can be added without guesswork.

## Current Capabilities
- **Modular Python package** with a central orchestrator and pluggable agents (filesystem, system health, developer helper, network diagnostics).
- **Four fully functional agents** with real system integration:
  - **FileSystemAgent**: Search files by pattern/size, list directories, get file info with safety checks
  - **SystemAgent**: Real-time CPU/memory/disk metrics, process listing, systemd service status, system health monitoring
  - **DeveloperAgent**: Git operations (status, log, branches), repository management, project workflows
  - **NetworkAgent**: Interface enumeration, ping/connectivity tests, DNS lookups, active connection monitoring
- **Self-Learning Personality System** (NEW!):
  - **UserPersonalityModel**: Learns your communication style (verbosity, technical level, formality) in real-time
  - **PromptOptimizationFilter**: Adapts every response to match your preferences
  - **Pattern Detection**: Identifies temporal patterns (what you do when) and sequential patterns (action A → action B)
  - **Privacy-First**: All learning stored locally in SQLite (`~/.maxos/personality.db`), no cloud telemetry
  - **Personality Inspection**: View learned preferences with `--show-personality` or export with `--export-personality`
- **Hybrid intent planner** backed by Pydantic schemas plus a graceful path for future LLM-powered planning.
- **Redis-backed conversation memory** for persistent, multi-session context.
- **CLI prototype** that parses intents and forwards them to the best-matching agent with structured responses, including a short-lived conversation memory buffer, JSON output mode, and transcript export.
- **Configuration loader** for environment + YAML settings, including placeholders for API keys and policy controls, and an LLM adapter that falls back to local stubs when keys are missing.
- **Structured logging** helper wired into the orchestrator so every request/response is audit-ready even without remote services.
- **Documentation set**: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/AGENT_IMPLEMENTATION.md`, `docs/PREDICTIVE_AGENT_ARCHITECTURE.md`, `docs/LEARNING_SYSTEM_DEMO.md`

## Getting Started

### 1. Setup Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2. Configure API Tokens
```bash
# Copy environment template
cp .env.example .env

# Copy config template
cp config/settings.example.yaml config/settings.yaml

# Edit .env and add your API keys (see docs/TOKEN_SETUP.md for detailed instructions)
# Required: ANTHROPIC_API_KEY
# Optional: OPENAI_API_KEY, GA_MEASUREMENT_ID, GA_API_SECRET
```

**📖 For detailed token setup instructions, see [docs/TOKEN_SETUP.md](docs/TOKEN_SETUP.md)**

### 3. Run MaxOS
```bash
python -m max_os.interfaces.cli.main "show system health"
```

**Example Commands**
```bash
# FileSystem operations
python -m max_os.interfaces.cli.main "search Downloads for .psd files larger than 200MB"
python -m max_os.interfaces.cli.main "list files in Documents"

# System monitoring
python -m max_os.interfaces.cli.main "show system health" --json | jq '{cpu, memory, disk}'
python -m max_os.interfaces.cli.main "show running processes"
python -m max_os.interfaces.cli.main "check docker service status"

# Developer workflows
python -m max_os.interfaces.cli.main "show git status"
python -m max_os.interfaces.cli.main "show recent commits"
python -m max_os.interfaces.cli.main "list git branches"

# Network diagnostics
python -m max_os.interfaces.cli.main "show network interfaces"
python -m max_os.interfaces.cli.main "ping google.com"
python -m max_os.interfaces.cli.main "dns lookup github.com"

# Personality Learning (learns from every interaction!)
python -m max_os.interfaces.cli.main --show-personality
python -m max_os.interfaces.cli.main --export-personality ~/my_personality.json
```

**Running the REST API**
```bash
uvicorn max_os.interfaces.api.main:app --reload
```

**Systemd service**
- A service template lives in `scripts/maxos.service`. Update `WorkingDirectory`/`ExecStart` to your install + virtualenv path (defaults assume `/opt/maxos/.venv`), set the service `User`/`Group` (defaults to `maxos`), and optionally set `AI_OS_CONFIG` in `/etc/maxos.env` before enabling.

**CLI Flags**
- `--json` prints only the payload (great for piping into `jq`).
- `--show-memory` echoes the in-memory transcript for the current session.
- `--dump-memory <path>` writes the transcript to disk for audits or follow-up prompts.
- `--show-personality` displays your learned personality model and preferences.
- `--export-personality <path>` exports personality model to JSON file.
- `--rollback <transaction_id>` rollback a filesystem operation.
- `--show-transactions` list recent filesystem transactions.
- `--show-trash` list files in trash that can be recovered.
- `--restore <transaction_id>` restore files from trash.

## New in Phase 2: Confirmation & Rollback Framework

MaxOS now includes a comprehensive confirmation and rollback system for safe filesystem operations:

**Features:**
- **Dry-run previews** - See what will happen before operations execute
- **User confirmation** - Approve/deny operations with detailed previews
- **Transaction logging** - All operations logged in SQLite database
- **Rollback support** - Undo copy, move, delete, and mkdir operations
- **Trash system** - Deleted files moved to `~/.maxos/trash/` with 30-day retention
- **Checksum verification** - SHA256 checksums ensure data integrity

**Example Workflow:**
```bash
# Operations require confirmation (unless auto-approved for small files)
# Copy operation shows preview and prompts for approval

# List recent transactions
python -m max_os.interfaces.cli.main --show-transactions

# View trash contents
python -m max_os.interfaces.cli.main --show-trash

# Rollback a transaction (undo copy/move/mkdir)
python -m max_os.interfaces.cli.main --rollback 123

# Restore deleted files from trash
python -m max_os.interfaces.cli.main --restore 124
```

**Configuration:**
Edit `config/settings.yaml`:
```yaml
agents:
  filesystem:
    confirmation:
      enabled: true
      require_for_operations: [copy, move, delete]
      auto_approve_under_mb: 10  # Auto-approve operations < 10MB
    rollback:
      enabled: true
      trash_retention_days: 30
      max_trash_size_gb: 50
```

## Repository Layout
```
ai-os/
├── max_os/
│   ├── core/            # Orchestrator + intent parsing
│   ├── agents/          # Specialized agent implementations
│   ├── interfaces/      # CLI prototype + voice/gui placeholders
│   └── utils/           # Config + logging helpers
├── config/              # Environment and policy templates
├── docs/                # Architecture + roadmap refs
├── scripts/             # Bootstrap + deployment helpers
└── tests/               # Pytest suites for orchestrator + agents
```

## Roadmap Snapshot
1. **Phase 0 – Foundations:** finalize tooling, finish stubs for every core agent, create CI + linting, and document security boundaries.
2. **Phase 1 – Core AI Engine:** wire live LLM provider, add Redis memory, and expose REST/gRPC API.
3. **Phase 2 – System Agents:** expand filesystem, package, and observability agents with real D-Bus/systemd bindings.
4. **Phase 3 – Voice & GUI:** integrate Whisper/Piper for voice IO and prototype the desktop shell.
5. **Phase 4 – Custom Distro:** convert scripts to Debian installer hooks, bake ISO, and add OTA update pipeline.

See `docs/ROADMAP.md` for detailed acceptance criteria and testing gates per phase.
