#!/bin/bash

# setup_remote_ssh.sh
# Ensures correct permissions on remote and optionally disables password auth.

set -e

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 user@host [disable-password]"
    echo "Example: $0 peter@192.168.20.12 disable-password"
    exit 1
fi

TARGET=$1
ACTION=$2
SSH_KEY_PUB="ssh/id_ed25519.pub"

if [ ! -f "$SSH_KEY_PUB" ]; then
    echo "❌ Error: Project public key not found at $SSH_KEY_PUB"
    exit 1
fi

echo "🔐 Setting up remote SSH for $TARGET..."

# 1. Fix permissions and ensure key is present
echo "📂 Ensuring .ssh directory and authorized_keys permissions..."
PUB_KEY_CONTENT=$(cat "$SSH_KEY_PUB")
ssh "$TARGET" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
               touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && \
               if ! grep -q \"$PUB_KEY_CONTENT\" ~/.ssh/authorized_keys; then \
                   echo \"$PUB_KEY_CONTENT\" >> ~/.ssh/authorized_keys; \
                   echo \"✅ Public key added to authorized_keys.\"; \
               else \
                   echo \"ℹ️ Public key already present.\"; \
               fi"

# 2. Optionally disable password authentication
if [ "$ACTION" == "disable-password" ]; then
    echo "🚫 Attempting to disable password authentication (requires sudo permissions on remote)..."
    ssh -t "$TARGET" "sudo sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
                      sudo sed -i 's/^#\?PubkeyAuthentication .*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
                      sudo systemctl restart ssh || sudo service ssh restart"
    echo "✅ Password authentication disabled and SSH service restarted."
    echo "⚠️  CRITICAL: Do not close this terminal! Test login in a new window first."
fi

echo "🎉 Remote setup complete."
