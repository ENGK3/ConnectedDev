#!/bin/bash
##############################################################################
# edit_config.sh
#
# Updates a phone number value in K3_config_settings file
#
# Usage: edit_config.sh <config_variable> <phone_number>
#
# Arguments:
#   config_variable - The config variable name (e.g., FIRST_NUMBER, SECOND_NUMBER, THIRD_NUMBER)
#   phone_number    - New phone number (1-30 digits) to set
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
if [ $# -ne 2 ]; then
    log "ERROR: Usage: $0 <config_variable> <phone_number>"
    exit 1
fi

CONFIG_VAR="$1"
PHONE_NUMBER="$2"

# Validate config variable name (must be alphanumeric and underscore)
if ! echo "$CONFIG_VAR" | grep -qE '^[A-Z_][A-Z0-9_]*$'; then
    log "ERROR: Invalid config variable name: $CONFIG_VAR"
    exit 1
fi

# Validate phone number (1-30 characters: digits, A-F, *, #)
if ! echo "$PHONE_NUMBER" | grep -qE '^[0-9A-F*#]{1,30}$'; then
    log "ERROR: Invalid phone number format: $PHONE_NUMBER (must be 1-30 characters: 0-9, A-F, *, #)"
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

# Save original ownership and permissions
ORIG_OWNER=$(stat -c '%U:%G' "$CONFIG_FILE")
ORIG_PERMS=$(stat -c '%a' "$CONFIG_FILE")

# Update config variable using sed
# This handles both quoted and unquoted values
if grep -q "^${CONFIG_VAR}=" "$CONFIG_FILE"; then
    # Replace existing value
    sed -i "s/^${CONFIG_VAR}=.*/${CONFIG_VAR}=\"$PHONE_NUMBER\"/" "$CONFIG_FILE"
    log "INFO: Updated ${CONFIG_VAR} to: $PHONE_NUMBER"
else
    # Variable doesn't exist, append it
    echo "${CONFIG_VAR}=\"$PHONE_NUMBER\"" >> "$CONFIG_FILE"
    log "INFO: Added ${CONFIG_VAR}: $PHONE_NUMBER"
fi

# Restore original ownership and permissions
# This ensures kuser:asterisk 664 is maintained regardless of who runs the script
chown "$ORIG_OWNER" "$CONFIG_FILE" 2>/dev/null || true
chmod "$ORIG_PERMS" "$CONFIG_FILE" 2>/dev/null || true

# Verify the change was made
if grep -q "^${CONFIG_VAR}=\"$PHONE_NUMBER\"" "$CONFIG_FILE"; then
    log "SUCCESS: ${CONFIG_VAR} successfully updated to $PHONE_NUMBER"

    # Keep only the last 10 backups
    ls -t "${BACKUP_DIR}/K3_config_settings_"*.bak 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

    exit 0
else
    log "ERROR: Failed to verify update. Restoring backup."
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    exit 1
fi
