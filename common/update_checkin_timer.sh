#!/bin/bash
#
# update_checkin_timer.sh - Update the EDC check-in timer based on K3_config_settings
#
# This script reads the CHECKIN_INTERVAL_DAYS from K3_config_settings and updates
# the send_edc_checkin.timer file with the appropriate interval values.
#
# Usage: ./update_checkin_timer.sh [--install]
#   --install  Copy timer to systemd directory and enable it
#
# This script should be run:
# 1. During initial installation (with --install flag)
# 2. After any changes to CHECKIN_INTERVAL_DAYS in K3_config_settings
#

set -e

# Configuration
CONFIG_FILE="/mnt/data/K3_config_settings"
TIMER_FILE="/etc/systemd/system/send_edc_checkin.timer"
SERVICE_FILE="/etc/systemd/system/send_edc_checkin.service"

# Default value if config not found
DEFAULT_INTERVAL_DAYS=1

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "Error: This script must be run as root"
   exit 1
fi

# Read the interval from config file
if [[ -f "$CONFIG_FILE" ]]; then
    # Source the config file to get CHECKIN_INTERVAL_DAYS
    source "$CONFIG_FILE"
    INTERVAL_DAYS="${CHECKIN_INTERVAL_DAYS:-$DEFAULT_INTERVAL_DAYS}"
else
    echo "Warning: Config file $CONFIG_FILE not found, using default interval of $DEFAULT_INTERVAL_DAYS day(s)"
    INTERVAL_DAYS=$DEFAULT_INTERVAL_DAYS
fi

echo "Setting check-in interval to $INTERVAL_DAYS day(s)"

# Update the timer file if it exists
if [[ -f "$TIMER_FILE" ]]; then
    sed -i "s/OnBootSec=.*/OnBootSec=${INTERVAL_DAYS}d/" "$TIMER_FILE"
    sed -i "s/OnUnitActiveSec=.*/OnUnitActiveSec=${INTERVAL_DAYS}d/" "$TIMER_FILE"
    echo "Updated timer file: $TIMER_FILE"

    # Reload systemd daemon
    systemctl daemon-reload
    echo "Systemd daemon reloaded"

    # Restart timer if it's active
    if systemctl is-active --quiet send_edc_checkin.timer; then
        systemctl restart send_edc_checkin.timer
        echo "Restarted send_edc_checkin.timer"
    fi
else
    echo "Warning: Timer file $TIMER_FILE not found"
fi

# Handle --install flag
if [[ "$1" == "--install" ]]; then
    echo "Installing EDC check-in timer..."

    # Copy service file if it exists in current directory
    if [[ -f "send_edc_checkin.service" ]]; then
        cp send_edc_checkin.service "$SERVICE_FILE"
        echo "Installed service file to $SERVICE_FILE"
    elif [[ ! -f "$SERVICE_FILE" ]]; then
        echo "Error: Service file not found in current directory or systemd directory"
        exit 1
    fi

    # Copy and update timer file
    if [[ -f "send_edc_checkin.timer" ]]; then
        cp send_edc_checkin.timer "$TIMER_FILE"
        # Update the intervals in the newly copied file
        sed -i "s/OnBootSec=.*/OnBootSec=${INTERVAL_DAYS}d/" "$TIMER_FILE"
        sed -i "s/OnUnitActiveSec=.*/OnUnitActiveSec=${INTERVAL_DAYS}d/" "$TIMER_FILE"
        echo "Installed and configured timer file to $TIMER_FILE"
    else
        echo "Error: Timer file not found in current directory"
        exit 1
    fi

    # Reload systemd and enable timer
    systemctl daemon-reload
    systemctl enable send_edc_checkin.timer
    systemctl start send_edc_checkin.timer

    echo "EDC check-in timer installed, enabled, and started"
    echo ""
    echo "Check status with: systemctl status send_edc_checkin.timer"
    echo "List timers with: systemctl list-timers send_edc_checkin.timer"
fi

# Display next scheduled run
if systemctl is-enabled --quiet send_edc_checkin.timer 2>/dev/null; then
    echo ""
    echo "Next scheduled run:"
    systemctl list-timers send_edc_checkin.timer --no-pager
fi
