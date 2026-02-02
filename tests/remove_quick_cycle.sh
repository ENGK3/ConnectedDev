#!/bin/bash
#
# Remove quick cycle testing configuration for send_edc_checkin.timer
# This restores the timer to use the configured interval from K3_config_settings
#

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root" >&2
    echo "Please use: sudo $0" >&2
    exit 1
fi

OVERRIDE_DIR="/etc/systemd/system/send_edc_checkin.timer.d"

echo "Removing quick cycle test configuration..."

# Check if override directory exists
if [ ! -d "${OVERRIDE_DIR}" ]; then
    echo "No quick cycle configuration found (${OVERRIDE_DIR} does not exist)"
    echo "Nothing to remove."
    exit 0
fi

# Remove the override directory
rm -rf "${OVERRIDE_DIR}"

if [ $? -eq 0 ]; then
    echo "✓ Removed override directory ${OVERRIDE_DIR}"
else
    echo "✗ Failed to remove override directory" >&2
    exit 1
fi

# Reload systemd to pick up the changes
echo "Reloading systemd daemon..."
systemctl daemon-reload

if [ $? -eq 0 ]; then
    echo "✓ Systemd daemon reloaded"
else
    echo "✗ Failed to reload systemd daemon" >&2
    exit 1
fi

# Restart the timer to apply original settings
echo "Restarting send_edc_checkin.timer..."
systemctl restart send_edc_checkin.timer

if [ $? -eq 0 ]; then
    echo "✓ Timer restarted successfully"
else
    echo "✗ Failed to restart timer" >&2
    exit 1
fi

echo ""
echo "Quick cycle test configuration removed successfully!"
echo "The timer has been restored to the configured interval."
echo ""
echo "Check the timer schedule with:"
echo "  systemctl list-timers send_edc_checkin.timer"
