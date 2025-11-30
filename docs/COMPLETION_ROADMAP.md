# MaxOS Completion Roadmap

This document outlines the detailed step-by-step instructions to bring MaxOS from its current "fully functional core" state to a complete, deployable Linux distribution with a native voice and graphical interface.

## Phase 3: Voice & GUI (The Interface Layer)

**Goal:** Transform MaxOS from a CLI tool into an interactive, multimodal desktop assistant.

### Step 3.1: Voice Input (Speech-to-Text)
1.  **Dependency Setup:**
    -   Add `openai-whisper` (or `faster-whisper`) to `pyproject.toml`.
    -   Ensure `ffmpeg` is available in the environment.
2.  **Implementation (`max_os/interfaces/voice/listener.py`):**
    -   Create a `VoiceListener` class.
    -   Implement a "Wake Word" engine (e.g., using `openwakeword` or `porcupine`) to listen for "Hey Max".
    -   Upon wake, capture audio stream until silence is detected (VAD - Voice Activity Detection).
    -   Pass audio buffer to Whisper model for transcription.
    -   Return text to the Orchestrator.

### Step 3.2: Voice Output (Text-to-Speech)
1.  **Dependency Setup:**
    -   Add `piper-tts` or `coqui-tts` to `pyproject.toml` (Piper is recommended for low latency/offline).
2.  **Implementation (`max_os/interfaces/voice/speaker.py`):**
    -   Create a `VoiceSpeaker` class.
    -   Implement `speak(text: str)` method.
    -   Ensure audio output is non-blocking (async) or handled in a separate thread so the UI doesn't freeze.
    -   Add caching for common phrases if necessary.

### Step 3.3: Desktop Shell (GUI)
1.  **Architecture Decision:**
    -   Use **Electron** or **Tauri** for the frontend to allow usage of modern web frameworks (React/Next.js).
    -   The GUI will communicate with the Python backend via a local REST API or WebSocket (FastAPI).
2.  **Frontend Setup (`max_os/interfaces/gui/frontend/`):**
    -   Initialize a new React project.
    -   Create a chat interface (similar to ChatGPT).
    -   Add visual indicators for "Listening", "Processing", and "Speaking".
    -   Implement a "System Dashboard" view to visualize metrics from `SystemAgent` (CPU, RAM, etc.).
3.  **Backend Integration (`max_os/interfaces/api/main.py`):**
    -   Ensure FastAPI exposes endpoints for:
        -   Sending user intents (text).
        -   Streaming agent responses (server-sent events).
        -   Broadcasting system state changes.

### Step 3.4: Multimodal Context
1.  **Shared Timeline:**
    -   Update `max_os/core/orchestrator.py` to maintain a unified event stream that includes voice transcripts, typed text, and GUI clicks.
    -   Ensure the `ContextAwarenessEngine` can read the state of the GUI (e.g., "what is the user looking at?").

---

## Phase 4: Linux Integration (The System Layer)

**Goal:** Deep integration with the host Linux OS, ensuring security and persistence.

### Step 4.1: Systemd Services
1.  **Service Definition (`scripts/maxos-core.service`):**
    -   Create a systemd unit file that runs the `maxos-orchestrator`.
    -   Ensure it restarts on failure (`Restart=always`).
    -   Set appropriate user/group permissions (should not run as root unless necessary).
2.  **Installation Script:**
    -   Update `scripts/install.sh` to copy the service file to `/etc/systemd/system/` and enable it.

### Step 4.2: PolicyKit & Security
1.  **Privilege Separation:**
    -   Identify which agent actions require root (e.g., installing packages, restarting services).
    -   Do **not** run the main Python process as root.
2.  **Polkit Rules (`config/polkit/`):**
    -   Create XML policy files defining custom actions (e.g., `org.maxos.manage-system`).
    -   Use `pkexec` within `SystemAgent` to request elevated privileges only when needed.

### Step 4.3: Packaging
1.  **Build Configuration:**
    -   Use tools like `fpm` or standard `dpkg-deb` workflows.
2.  **DEB Package:**
    -   Create `debian/control` file defining dependencies (`python3`, `ffmpeg`, etc.).
    -   Create `debian/postinst` to set up the `maxos` user and groups.
    -   Build the `.deb` package.

---

## Phase 5: Custom Distro & OTA (The Product Layer)

**Goal:** A standalone OS installation media (ISO) that installs MaxOS by default.

### Step 5.1: Base Image Construction
1.  **Tooling:**
    -   Use **Cubic** (Custom Ubuntu ISO Creator) or a `preseed` configuration with Debian.
2.  **Customization:**
    -   Start with a minimal Ubuntu 24.04 LTS server or Debian Stable base.
    -   Remove unnecessary packages (e.g., cloud-init if for desktop).
    -   Install the MaxOS `.deb` package created in Phase 4.
    -   Configure the desktop environment (GNOME/KDE) to launch the MaxOS GUI shell on login.

### Step 5.2: Installer Hooks
1.  **First-Run Experience:**
    -   Create a "Welcome" script that runs on first boot.
    -   Guide the user through creating a user account and connecting to WiFi.
    -   Initialize the `UserPersonalityModel`.

### Step 5.3: Over-the-Air (OTA) Updates
1.  **Update Mechanism:**
    -   Implement a mechanism (e.g., using `ostree` or a simple git-pull based updater for the python code).
    -   The `SystemAgent` should be able to check for updates and apply them.
2.  **Rollback:**
    -   Ensure the system can boot into a previous state if an update fails (btrfs snapshots are recommended).

## Definition of Done

The project is considered complete when:
1.  You can speak to the OS ("Hey Max") and get a spoken response.
2.  A GUI window shows the conversation history and system stats.
3.  The software is installed as a system service, persisting across reboots.
4.  Privileged actions are handled securely without running the whole app as root.
5.  An ISO image exists that can install this environment on a bare-metal machine.
