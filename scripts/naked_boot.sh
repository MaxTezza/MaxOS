#!/bin/bash
# MaxOS V3 "Naked Boot" Setup Script
# Configures the host to launch MaxOS as the primary interface.

echo "🌑 Configuring MaxOS Naked Boot..."

# 1. Ensure Dependencies
sudo apt-get update
sudo apt-get install -y xserver-xorg xinit xterm python3-pip

# 2. Create the .xinitrc if not exists
cat <<EOF > ~/.xinitrc
# Launch the MaxOS Runner
# We use a simple window manager like 'openbox' or just run the runner directly in X
exec python3 runner.py --fullscreen
EOF

# 3. Instruction for Auto-Login (High Risk - Requires User Confirmation)
echo "--------------------------------------------------------"
echo "To finish the Naked Boot setup:"
echo "1. Run: sudo systemctl set-default multi-user.target"
echo "2. Edit /etc/systemd/system/getty@tty1.service.d/override.conf"
echo "3. Add: ExecStart=-/sbin/agetty --autologin $(whoami) --noclear %I \$TERM"
echo "--------------------------------------------------------"

echo "✅ MaxOS is prepared for Naked Boot. Type 'startx' to enter the AI-OS."
