#!/usr/bin/env bash
# MaxOS Bootstrap Script
# Installs system dependencies and sets up the development environment

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 MaxOS Bootstrap Script"
echo "========================="
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root. Please run without sudo."
   echo "   (It will prompt for sudo when needed)"
   exit 1
fi

# Detect package manager
if command -v apt &> /dev/null; then
    PKG_MGR="apt"
    INSTALL_CMD="sudo apt install -y"
elif command -v dnf &> /dev/null; then
    PKG_MGR="dnf"
    INSTALL_CMD="sudo dnf install -y"
elif command -v pacman &> /dev/null; then
    PKG_MGR="pacman"
    INSTALL_CMD="sudo pacman -S --noconfirm"
else
    echo "⚠️  Could not detect package manager. Skipping system dependencies."
    echo "   You may need to install: python3-dev libdbus-1-dev pkg-config"
    PKG_MGR=""
fi

if [[ -n "$PKG_MGR" ]]; then
    echo "📦 Detected package manager: $PKG_MGR"
    echo ""
    echo "Would you like to install system dependencies? (y/n)"
    read -r install_deps

    if [[ "$install_deps" == "y" ]]; then
        echo "📥 Installing system dependencies..."

        if [[ "$PKG_MGR" == "apt" ]]; then
            sudo apt update
            $INSTALL_CMD \
                python3-dev \
                python3-pip \
                python3-venv \
                libdbus-1-dev \
                libdbus-glib-1-dev \
                pkg-config \
                build-essential \
                systemd \
                policykit-1 || echo "⚠️ Some packages may have failed to install"
        elif [[ "$PKG_MGR" == "dnf" ]]; then
            $INSTALL_CMD \
                python3-devel \
                python3-pip \
                dbus-devel \
                dbus-glib-devel \
                pkgconfig \
                gcc \
                systemd \
                polkit || echo "⚠️ Some packages may have failed to install"
        elif [[ "$PKG_MGR" == "pacman" ]]; then
            $INSTALL_CMD \
                python \
                python-pip \
                dbus \
                dbus-glib \
                pkgconf \
                base-devel \
                systemd \
                polkit || echo "⚠️ Some packages may have failed to install"
        fi
        echo "✅ System dependencies installed"
    fi
fi

# Set up Python virtual environment
echo ""
echo "🐍 Setting up Python virtual environment..."

if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi

# Activate and upgrade pip
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install MaxOS
echo ""
echo "📦 Installing MaxOS package..."
pip install -e .[dev]

# Try installing systemd extras if dependencies are available
if command -v pkg-config &> /dev/null && pkg-config --exists dbus-1; then
    echo "📦 Installing systemd integration..."
    pip install -e .[systemd] || echo "⚠️  D-Bus Python binding failed to install. Systemd features will be limited."
fi

echo "✅ MaxOS installed"

# Create config directory
echo ""
echo "⚙️  Setting up configuration..."

mkdir -p config logs

if [[ ! -f "config/settings.yaml" ]]; then
    if [[ -f "config/settings.example.yaml" ]]; then
        cp config/settings.example.yaml config/settings.yaml
    else
        cat > config/settings.yaml <<EOF
# MaxOS Configuration
log_level: INFO
log_format: json
log_file: logs/maxos.log

# LLM Provider (google or local)
llm_provider: local
llm_model: stub

# API Keys (optional - leave empty to use local stub)
google_api_key: ""

# Agent Configuration
agents:
  filesystem:
    enabled: true
    max_file_size_mb: 1000
  developer:
    enabled: true
    default_editor: code
  system:
    enabled: true
    allow_service_control: false
  network:
    enabled: true
    allow_firewall_changes: false

# Security
require_confirmation: true
audit_log: logs/audit.log
EOF
    fi
    echo "✅ Configuration file created at config/settings.yaml"
else
    echo "ℹ️  Configuration file already exists"
fi

# Create systemd user service (optional)
echo ""
echo "🔧 Would you like to install the systemd user service? (y/n)"
read -r install_service

if [[ "$install_service" == "y" ]]; then
    mkdir -p ~/.config/systemd/user/
    cat > ~/.config/systemd/user/maxos.service <<EOF
[Unit]
Description=MaxOS API Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/.venv/bin/uvicorn max_os.interfaces.api.main:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    echo "✅ Systemd service installed"
    echo "   Enable with: systemctl --user enable maxos"
    echo "   Start with: systemctl --user start maxos"
else
    echo "ℹ️  Skipping systemd service installation"
fi

echo ""
echo "🎉 Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment: source .venv/bin/activate"
echo "  2. Configure API keys in config/settings.yaml (optional)"
echo "  3. Test the CLI: python -m max_os.interfaces.cli.main --help"
echo "  4. Run tests: pytest"
echo ""
echo "Example commands:"
echo "  python -m max_os.interfaces.cli.main 'scan Downloads for .psd files'"
echo "  python -m max_os.interfaces.cli.main --json 'check system health'"
echo ""
