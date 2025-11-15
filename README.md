# MaxOS

Natural-language control plane for Linux that routes user intents to trusted autonomous agents. This repo contains the scaffolding, documentation, and first reference implementations for the MaxOS experiment described in the internal white papers.

## Why This Exists
- Treat the OS as a conversation: describe your goal once, let orchestrated agents execute the steps.
- Ship a privacy-conscious stack that can run fully offline with local LLMs but can burst to cloud APIs.
- Provide opinionated guidance (architecture, security, deployment) so additional agents can be added without guesswork.

## Current Capabilities
- Modular Python package with a central orchestrator and pluggable agents (filesystem, system health, developer helper, network bootstrapper).
- Hybrid intent planner backed by Pydantic schemas plus a graceful path for future LLM-powered planning.
- CLI prototype that parses intents and forwards them to the best-matching agent with structured responses, including a short-lived conversation memory buffer, JSON output mode, and transcript export.
- Configuration loader for environment + YAML settings, including placeholders for API keys and policy controls, and an LLM adapter that falls back to local stubs when keys are missing.
- Structured logging helper wired into the orchestrator so every request/response is audit-ready even without remote services.
- Documentation set: `docs/ARCHITECTURE.md` (component matrix, Linux integration notes) and `docs/ROADMAP.md` (phased plan sourced from the master roadmap).

## Getting Started
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp config/settings.example.yaml config/settings.yaml
python -m max_os.interfaces.cli.main --show-memory "scan Downloads for .psd files larger than 200MB"
```

**CLI Flags**
- `--json` prints only the payload (great for piping into `jq`).
- `--show-memory` echoes the in-memory transcript for the current session.
- `--dump-memory <path>` writes the transcript to disk for audits or follow-up prompts.

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
