#!/usr/bin/env bash
#
# Linux Hardening Script
# Applies basic SSH hardening and firewall rules.
# WARNING: Modifies system configuration. Review before running.
# Designed to be safe to re-run (idempotent) where possible.

set -euo pipefail

SSHD_CONFIG="/etc/ssh/sshd_config"
BACKUP_SUFFIX=".bak.$(date +%Y%m%d%H%M%S)"

echo "=== Linux Hardening Script ==="
echo "This will modify SSH configuration and firewall rules."
read -p "Continue? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

# --- SSH Hardening ---
if [[ -f "$SSHD_CONFIG" ]]; then
    echo "Backing up $SSHD_CONFIG to ${SSHD_CONFIG}${BACKUP_SUFFIX}"
    sudo cp "$SSHD_CONFIG" "${SSHD_CONFIG}${BACKUP_SUFFIX}"

    echo "Disabling root login over SSH..."
    sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' "$SSHD_CONFIG"

    echo "Disabling password authentication (key-only)..."
    sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"

    echo "Disabling empty passwords..."
    sudo sed -i 's/^#*PermitEmptyPasswords.*/PermitEmptyPasswords no/' "$SSHD_CONFIG"

    echo "SSH config updated. Restart sshd to apply: sudo systemctl restart sshd"
else
    echo "sshd_config not found at $SSHD_CONFIG — skipping SSH hardening (is OpenSSH installed?)"
fi

# --- Basic Firewall Rules (using ufw if available) ---
if command -v ufw &> /dev/null; then
    echo "Configuring firewall with ufw..."
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    echo "Firewall rules set: deny all inbound except SSH, allow all outbound."
    echo "Enable with: sudo ufw enable"
elif command -v firewall-cmd &> /dev/null; then
    echo "Configuring firewall with firewalld..."
    sudo firewall-cmd --set-default-zone=drop
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --reload
    echo "Firewall rules set: default drop, SSH allowed."
else
    echo "No supported firewall tool (ufw/firewalld) found — skipping firewall hardening."
    echo "Consider installing ufw: sudo pacman -S ufw"
fi

echo ""
echo "=== Hardening complete ==="
echo "Backup of original sshd_config saved with suffix: ${BACKUP_SUFFIX}"
echo "Run 'sudo lynis audit system' to measure the security improvement."

