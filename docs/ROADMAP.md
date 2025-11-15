# MaxOS Roadmap

## Phase 0 – Foundations (Weeks 1-2)
- Finalize tooling (Python 3.11, Ruff, Black, Pytest, pre-commit).
- Ship stubs for orchestrator + all core agents with docstrings/tests.
- Document security posture (PolicyKit, audit logging, secrets management).
- Deliver bootstrap script that installs system dependencies and seeds `.env` / `config/settings.yaml`.

## Phase 1 – Core AI Engine (Weeks 3-6)
- Integrate LLM provider (start with Anthropic or local Llama via llama.cpp binding).
- Implement intent parser + planner with structured schema (Pydantic models).
- Add Redis (or LiteLLM memory) for short-term context; persist transcripts in SQLite.
- Expose orchestrator via REST (FastAPI) and gRPC for other clients.
- Tests: 90% unit coverage on parser + routing, contract tests for HTTP APIs.

## Phase 2 – System Agents (Weeks 7-10)
- Flesh out FileSystem, System, Network agents with real D-Bus/systemd/policy hooks.
- Implement confirmation + rollback framework (dry-run, diff previews, patch storage).
- Add observability stack: OpenTelemetry traces, structured logs, health endpoints.
- Create synthetic workloads + chaos tests to validate privilege boundaries.

## Phase 3 – Voice & GUI (Weeks 11-13)
- Package Whisper/Piper containers for offline voice IO; add wake-word listener.
- Build React/Next.js desktop shell (webview + native electron wrapper) for chat, notifications, and workflow history.
- Synchronize multimodal context (voice, text, GUI actions) through a shared timeline service.
- Usability testing with scripted scenarios; capture latency + transcription accuracy metrics.

## Phase 4 – Linux Integration (Weeks 14-17)
- Provide deb/rpm installers, systemd units, and PolicyKit profiles.
- Harden security with AppArmor/SELinux profiles, vault secrets, and signed agent bundles.
- Author admin guide (backup, upgrades, incident response) and integrate log shipping.

## Phase 5 – Custom Distro & OTA (Weeks 18-26)
- Fork Ubuntu 24.04 or Debian Sid using Cubic or distrobox, bake MaxOS preinstall.
- Add first-run wizard, secure boot assets, and OTA update service (rauc or swupd).
- Run closed beta with telemetry opt-in, publish ISO + checksum, document rollback.

## Liftoff Criteria
- ✅ Automated tests + lint run via CI on every push.
- ✅ Security review completed for orchestrator + privileged agents.
- ✅ Voice + GUI shells pass accessibility + localization smoke tests.
- ✅ Installable image boots on reference hardware (NUC + laptop) with recovery instructions.
