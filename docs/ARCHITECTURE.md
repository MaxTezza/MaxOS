# MaxOS Architecture

## 1. Vision
MaxOS reframes the operating system as an intent-driven platform. Users speak or type goals, a central orchestrator parses intent, and a bench of specialized agents executes those goals through Linux-native APIs (D-Bus, systemd, PolicyKit, etc.). The architecture must stay:
- **Model-agnostic:** swap GPT-4, Claude, Llama, or Mixtral without code churn.
- **Audit-friendly:** every agent action is logged with enough context for replay.
- **Extensible:** teams can add domain agents (media, CAD, finance) without touching the core.

## 2. Component Matrix
| Component            | Responsibilities                                               | Key Interfaces                            | Escalation Path                |
|----------------------|----------------------------------------------------------------|-------------------------------------------|--------------------------------|
| Central Orchestrator | Parse intent, plan multi-step tasks, own global context        | gRPC/REST API, Redis queue, memory store  | Calls PolicyKit broker         |
| Developer Agent      | Project scaffolding, code edits, CI triggers                   | Git CLI, VS Code Remote, GitHub Actions   | Delegates FS ops to FS Agent   |
| FileSystem Agent     | CRUD on files, package install, backups                        | libfsnotify, rsync, apt/dnf, btrfs tools  | Requests sudo via PolicyKit    |
| System Agent         | Observability, service health, remediation                     | systemd D-Bus, journalctl, psutil         | Sends unit overrides to systemd|
| Network Agent        | Wi-Fi/VPN setup, firewall rules, diagnostics                   | NetworkManager D-Bus, nftables            | PolicyKit -> netadmin profile  |
| Knowledge Agent      | Summaries, briefings, doc ingestion                            | Local embeddings, ElasticSearch           | None                           |
| UX Agent             | Voice/GUI layer, conversation memory sync                      | Whisper/Coqui STT, Piper TTS, React shell | Calls orchestrator callbacks   |

## 3. Intent & Memory Layer
- **Intent Planner:** `max_os/core/planner.py` uses keyword rules as fallback and emits structured `Intent` objects.
- **LLM-Powered Intent Classifier:** `max_os/core/intent_classifier.py` uses Claude/GPT-4 for intelligent natural language understanding with automatic fallback to keyword rules when LLM unavailable. Features:
  - **System Prompt Engineering:** `max_os/core/prompts.py` provides carefully crafted prompts with few-shot examples describing all MaxOS agent capabilities
  - **Entity Extraction:** `max_os/core/entities.py` parses LLM JSON responses to extract structured entities (file paths, sizes, service names)
  - **Confidence Calibration:** LLM returns 0.0-1.0 confidence scores for better intent disambiguation
  - **Context-Aware:** Leverages git status, active windows, and previous actions for improved accuracy
  - **Security Validation:** Validates extracted paths against whitelist, sanitizes user input before LLM submission
- **LLM Adapter:** `max_os/utils/llm_api.py` hides provider differences (Anthropic/OpenAI) with timeout handling, retry logic, and graceful fallback. Falls back to keyword rules when API keys not configured.
- **Conversation Memory:** `max_os/core/memory.py` holds the last N turns, suitable for short-context planning; persistence hooks write transcripts to disk or Redis in later phases.

### 3.1 LLM Intent Classification Pipeline

```
User Input → Intent Classifier
    ↓
1. Build LLM Prompt (system message + few-shot examples + context)
2. Call LLM API (Anthropic Claude or OpenAI GPT-4)
    ↓ Success              ↓ Failure/Timeout
3. Parse JSON Response    → Fallback to Keyword Rules
4. Extract Entities
5. Validate Paths
    ↓
Intent Object with Confidence + Entities
```

**Example Flow:**
```
Input: "copy Documents/report.pdf to Backup folder"

LLM Response:
{
  "intent": "file.copy",
  "confidence": 0.95,
  "entities": {
    "source_path": "Documents/report.pdf",
    "dest_path": "Backup"
  },
  "summary": "Copy report.pdf to Backup folder"
}

Result: Intent(
  name="file.copy",
  confidence=0.95,
  slots=[
    Slot(name="source_path", value="Documents/report.pdf"),
    Slot(name="dest_path", value="Backup")
  ]
)
```

### 3.2 Fallback Mechanisms

MaxOS implements multiple fallback layers for reliability:

1. **LLM Available:** Primary classification via Claude/GPT-4
2. **LLM Timeout:** Retry with exponential backoff (3 attempts, 10s timeout)
3. **LLM Unavailable:** Automatic fallback to keyword rules (offline mode)
4. **Context-Aware Rules:** Git status + active window heuristics
5. **Default Intent:** Low-confidence general intent as last resort

This ensures MaxOS works reliably even without internet connectivity or API keys.

## 4. Linux Integration Layer
- **D-Bus Calls:** e.g., `org.freedesktop.systemd1.Manager.StartUnit` with transient units for agent jobs.
- **PolicyKit Rules:** `/etc/polkit-1/rules.d/90-maxos.rules` grants specific agents rights: `if (subject.local && subject.user == "maxos") return polkit.Result.YES;`.
- **systemd Units:** `maxos.service` launches the orchestrator, while `maxos-agent@.service` templates sandbox each agent with `DynamicUser=yes` and `PrivateTmp=yes`.
- **Audit Trail:** every privileged command emits a JSON line to `/var/lib/maxos/audit.log` with checksum + parent intent. A cron job syncs logs to secure storage.
- **Rollback:** filesystem agent writes diffs under `/var/lib/maxos/change-log/<timestamp>.patch` so administrators can revert command batches quickly.

## 5. Logging & Observability
- `max_os/utils/logging.py` configures JSON or plain-text logs based on `config/settings.yaml` and writes to both stdout and `logs/maxos.log` by default.
- The orchestrator logs every planned intent and agent response; future work will add OpenTelemetry spans and metrics for queue depth, latency, and error counts.
- CLI operators can emit transcripts via `--dump-memory` for human-readable audits until the Redis/SQLite store is online.

## 6. Security & Trust Model
Threats and mitigations:
- **Intent spoofing:** sign UI payloads, require mTLS when remote clients talk to the orchestrator.
- **Privilege escalation:** use PolicyKit scopes per agent, AppArmor profiles (`/etc/apparmor.d/maxos.filesystem`) prevent arbitrary syscalls.
- **Data exfiltration:** sensitive commands force interactive confirmation; outbound network is proxied/logged; redact secrets in logs by default.
- **Agent tampering:** agents are versioned bundles with SHA256 manifest. The orchestrator verifies checksum before activation and can hot-revoke compromised agents.

## 7. Example Workflows
### 7.1 File Cleanup
1. User: "Archive every `.psd` in Downloads larger than 200 MB."
2. Orchestrator detects `file.cleanup` intent → FileSystem Agent.
3. Agent lists matches, asks for confirmation, creates tarball, updates audit log, responds with path.

### 7.2 Project Scaffolding
1. User: "Set up a FastAPI backend with a React dashboard and push to GitHub."
2. Orchestrator sequences Developer Agent (scaffold repo, configure CI) + FileSystem Agent (compose files) + System Agent (install packages) + Git integration.
3. Response includes repo URL, commands run, CI status.

### 7.3 System Health
1. User: "Why is my fan screaming?"
2. Orchestrator calls System Agent to gather `sensors`, `journalctl`, `psutil` metrics.
3. Agent proposes remediation (kill runaway process, lower GPU clock). Changes gated on user confirmation.

## 8. Implementation Status
- ✅ Repository scaffolding (this repo)
- ✅ LLM-powered intent classification with entity extraction (Phase 1)
- ✅ Anthropic Claude & OpenAI GPT-4 integration
- ✅ Automatic fallback to keyword rules (offline mode)
- ✅ Context-aware intent resolution (git status, active windows)
- ✅ Entity validation and path security checks
- 🚧 Concrete D-Bus bindings
- 🔜 Voice + GUI shells

Contributions should link architecture decisions back to this document; update the matrix/table when new agents or interfaces ship.
