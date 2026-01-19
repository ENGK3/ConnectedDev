#!/bin/bash
##############################################################################
# edit_primary_phone.sh
#
# Updates the SECOND_NUMBER value in K3_config_settings file
#
# Usage: edit_second_phone.sh <phone_number>
#
# Arguments:
#   phone_number - New phone number (1-30 digits) to set as FIRST_NUMBER
#
# Returns:
#   0 - Success
#   1 - Error (invalid arguments, file not found, etc.)
##############################################################################

set -e

# Configuration
CONFIG_FILE="/mnt/data/K3_config_settings"
BACKUP_DIR="/mnt/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /mnt/data/calls.log
}

# Validate arguments
if [ $# -ne 1 ]; then
    log "ERROR: Usage: $0 <phone_number>"
    exit 1
fi

PHONE_NUMBER="$1"

# Validate phone number (1-30 digits only)
if ! echo "$PHONE_NUMBER" | grep -qE '^[0-9]{1,30}$'; then
    log "ERROR: Invalid phone number format: $PHONE_NUMBER (must be 1-30 digits)"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    log "ERROR: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR" 2>/dev/null || true

# Backup the original file
BACKUP_FILE="${BACKUP_DIR}/K3_config_settings_${TIMESTAMP}.bak"
cp "$CONFIG_FILE" "$BACKUP_FILE"
log "INFO: Backed up config to: $BACKUP_FILE"

# Update FIRST_NUMBER using sed
# This handles both quoted and unquoted values
if grep -q '^SECOND_NUMBER=' "$CONFIG_FILE"; then
    # Replace existing FIRST_NUMBER value
    sed -i "s/^SECOND_NUMBER=.*/SECOND_NUMBER=\"$PHONE_NUMBER\"/" "$CONFIG_FILE"
    log "INFO: Updated FIRST_NUMBER to: $PHONE_NUMBER"
else
    # SECOND_NUMBER doesn't exist, append it
    echo "SECOND_NUMBER=\"$PHONE_NUMBER\"" >> "$CONFIG_FILE"
    log "INFO: Added SECOND_NUMBER: $PHONE_NUMBER"
fi

# Verify the change was made
if grep -q "^SECOND_NUMBER=\"$PHONE_NUMBER\"" "$CONFIG_FILE"; then
    log "SUCCESS: SECOND_NUMBER successfully updated to $PHONE_NUMBER"

    # Keep only the last 10 backups
    ls -t "${BACKUP_DIR}/K3_config_settings_"*.bak 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

    exit 0
else
    log "ERROR: Failed to verify update. Restoring backup."
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    exit 1
fi
