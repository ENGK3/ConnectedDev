#!/bin/bash
#
# Install quick cycle testing configuration for send_edc_checkin.timer
# This overrides the timer to run every 2 minutes instead of the configured days
#

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root" >&2
    echo "Please use: sudo $0" >&2
    exit 1
fi

OVERRIDE_DIR="/etc/systemd/system/send_edc_checkin.timer.d"
OVERRIDE_FILE="${OVERRIDE_DIR}/testing.conf"

echo "Installing quick cycle test configuration..."

# Create the override directory
mkdir -p "${OVERRIDE_DIR}"

# Create the override configuration
cat > "${OVERRIDE_FILE}" <<'EOF'
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
EOF

if [ $? -eq 0 ]; then
    echo "✓ Created override configuration at ${OVERRIDE_FILE}"
else
    echo "✗ Failed to create override configuration" >&2
    exit 1
fi

# Reload systemd to pick up the override
echo "Reloading systemd daemon..."
systemctl daemon-reload

if [ $? -eq 0 ]; then
    echo "✓ Systemd daemon reloaded"
else
    echo "✗ Failed to reload systemd daemon" >&2
    exit 1
fi

# Restart the timer to apply new settings
echo "Restarting send_edc_checkin.timer..."
systemctl restart send_edc_checkin.timer

if [ $? -eq 0 ]; then
    echo "✓ Timer restarted successfully"
else
    echo "✗ Failed to restart timer" >&2
    exit 1
fi

echo ""
echo "Quick cycle test configuration installed successfully!"
echo "The timer will now trigger every 2 minutes."
echo ""
echo "Monitor the timer with:"
echo "  watch -n 5 'systemctl list-timers send_edc_checkin.timer'"
echo ""
echo "View logs with:"
echo "  journalctl -u send_edc_checkin.service -f"
echo ""
echo "To remove the quick cycle configuration, run:"
echo "  sudo $(dirname "$0")/remove_quick_cycle.sh"
