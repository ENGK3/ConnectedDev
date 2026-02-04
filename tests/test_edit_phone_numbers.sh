#!/bin/bash
##############################################################################
# test_edit_phone_numbers.sh
#
# Test script for DTMF phone number editing features via Asterisk
#   01# - Edit FIRST_NUMBER
#   02# - Edit SECOND_NUMBER
#   03# - Edit THIRD_NUMBER
#
# Prerequisites:
#   - SSH access to target host (for remote testing)
#   - baresip client available on the target
#   - Asterisk running with the new configuration
#   - Admin extension (200 or 201) configured
#
# Usage: ./test_edit_phone_numbers.sh [TARGET_HOST] [CONFIG_FILE] [SCRIPT_PATH]
#   TARGET_HOST: SSH target (e.g., root@GWorks2) or "local" for local testing [default: root@GWorks2]
#   CONFIG_FILE: Path to K3_config_settings file [default: /mnt/data/K3_config_settings]
#   SCRIPT_PATH: Path to edit_config.sh script [default: /mnt/data/edit_config.sh]
#
# Examples:
#   ./test_edit_phone_numbers.sh                          # Remote test with defaults
#   ./test_edit_phone_numbers.sh local                    # Local test with defaults
#   ./test_edit_phone_numbers.sh local /tmp/test_config ../common/edit_config.sh
##############################################################################

set -e

# Parse command line arguments
TARGET_HOST="${1:-root@GWorks2}"
CONFIG_FILE="${2:-/mnt/data/K3_config_settings}"

# Determine if we're testing locally or remotely
if [ "$TARGET_HOST" = "local" ]; then
    IS_LOCAL=true
    # For local testing, default to the script in the common directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    SCRIPT_PATH="${3:-$SCRIPT_DIR/common/edit_config.sh}"
else
    IS_LOCAL=false
    SCRIPT_PATH="${3:-/mnt/data/edit_config.sh}"
fi

TEST_PHONE_NUMBER_1="5551234567"
TEST_PHONE_NUMBER_2="5552345678"
TEST_PHONE_NUMBER_3="5553456789"
TEST_PHONE_STAR="*558881114321"
TEST_PHONE_HASH="#549128234567"
TEST_PHONE_BOTH="*549128234567#"
ORIGINAL_FIRST=""
ORIGINAL_SECOND=""
ORIGINAL_THIRD=""
TEST_PASSED=0
TEST_FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to run commands locally or remotely
run_cmd() {
    if [ "$IS_LOCAL" = true ]; then
        eval "$1"
    else
        ssh "$TARGET_HOST" "$1"
    fi
}

# Helper function to run script locally or remotely
run_script() {
    local var_name="$1"
    local phone_number="$2"
    if [ "$IS_LOCAL" = true ]; then
        "$SCRIPT_PATH" "$var_name" "$phone_number"
    else
        ssh "$TARGET_HOST" "$SCRIPT_PATH $var_name $phone_number"
    fi
}

# Setup local test environment
setup_local_test() {
    if [ "$IS_LOCAL" != true ]; then
        return 0
    fi

    log_info "Setting up local test environment..."

    # Handle directory path - assume K3_config_settings file inside
    if [ -d "$CONFIG_FILE" ]; then
        CONFIG_FILE="$CONFIG_FILE/K3_config_settings"
        log_info "Using config file in directory: $CONFIG_FILE"
    fi

    # If using default paths, create a temporary test environment
    if [ "$CONFIG_FILE" = "/mnt/data/K3_config_settings" ]; then
        TEST_DIR="/tmp/edit_config_test_$$"
        CONFIG_FILE="$TEST_DIR/K3_config_settings"
        mkdir -p "$TEST_DIR"
        mkdir -p "$TEST_DIR/backups"

        # Create a test config file
        cat > "$CONFIG_FILE" << 'EOF'
FIRST_NUMBER="1234567890"
SECOND_NUMBER="9876543210"
THIRD_NUMBER="5555555555"
EOF

        log_info "Created temporary test directory: $TEST_DIR"
        log_info "Using test config: $CONFIG_FILE"

        # Determine backup and log directories
        BACKUP_DIR="$TEST_DIR/backups"
        LOG_FILE="$TEST_DIR/calls.log"
    else
        # Using custom config file - create backup directory alongside it
        CONFIG_DIR="$(dirname "$CONFIG_FILE")"
        BACKUP_DIR="$CONFIG_DIR/backups"
        LOG_FILE="$CONFIG_DIR/calls.log"

        # Create config file if it doesn't exist
        if [ ! -f "$CONFIG_FILE" ]; then
            mkdir -p "$CONFIG_DIR"
            cat > "$CONFIG_FILE" << 'EOF'
FIRST_NUMBER="1234567890"
SECOND_NUMBER="9876543210"
THIRD_NUMBER="5555555555"
EOF
            log_info "Created test config file: $CONFIG_FILE"
        fi

        # Create backup directory
        mkdir -p "$BACKUP_DIR"
    fi

    # Always create a modified script for local testing that uses the correct paths
    TEMP_SCRIPT="/tmp/edit_config_test_script_$$.sh"
    sed "s|/mnt/data/K3_config_settings|$CONFIG_FILE|g; s|/mnt/data/backups|$BACKUP_DIR|g; s|/mnt/data/calls.log|$LOG_FILE|g" "$SCRIPT_PATH" > "$TEMP_SCRIPT"
    chmod +x "$TEMP_SCRIPT"
    SCRIPT_PATH="$TEMP_SCRIPT"

    log_info "Created modified script: $TEMP_SCRIPT"
}

# Cleanup local test environment
cleanup_local_test() {
    if [ "$IS_LOCAL" != true ]; then
        return 0
    fi

    log_info "Cleaning up local test environment..."

    # Clean up the temporary script
    if [ -n "$TEMP_SCRIPT" ] && [ -f "$TEMP_SCRIPT" ]; then
        rm -f "$TEMP_SCRIPT"
    fi

    # Clean up the test directory if we created one
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $*"
    TEST_PASSED=$((TEST_PASSED + 1))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $*"
    TEST_FAILED=$((TEST_FAILED + 1))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

# Test if SSH connection works
test_ssh_connection() {
    if [ "$IS_LOCAL" = true ]; then
        log_info "Testing locally, skipping SSH connection test"
        return 0
    fi

    log_info "Testing SSH connection to $TARGET_HOST..."
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "$TARGET_HOST" "echo 'Connected'" &>/dev/null; then
        log_success "SSH connection successful"
        return 0
    else
        log_error "Cannot connect to $TARGET_HOST. Please check SSH access."
        return 1
    fi
}

# Get current phone number values
get_current_phone_numbers() {
    log_info "Reading current phone number values..."

    ORIGINAL_FIRST=$(run_cmd "grep '^FIRST_NUMBER=' '$CONFIG_FILE' 2>/dev/null | cut -d'=' -f2 | tr -d '\"'")
    ORIGINAL_SECOND=$(run_cmd "grep '^SECOND_NUMBER=' '$CONFIG_FILE' 2>/dev/null | cut -d'=' -f2 | tr -d '\"'")
    ORIGINAL_THIRD=$(run_cmd "grep '^THIRD_NUMBER=' '$CONFIG_FILE' 2>/dev/null | cut -d'=' -f2 | tr -d '\"'")

    if [ -n "$ORIGINAL_FIRST" ]; then
        log_info "Current FIRST_NUMBER: $ORIGINAL_FIRST"
    else
        log_warn "FIRST_NUMBER not found in config file"
    fi

    if [ -n "$ORIGINAL_SECOND" ]; then
        log_info "Current SECOND_NUMBER: $ORIGINAL_SECOND"
    else
        log_warn "SECOND_NUMBER not found in config file"
    fi

    if [ -n "$ORIGINAL_THIRD" ]; then
        log_info "Current THIRD_NUMBER: $ORIGINAL_THIRD"
    else
        log_warn "THIRD_NUMBER not found in config file"
    fi
}

# Test the edit_config.sh script with a specific phone number variable
test_phone_number() {
    local VAR_NAME="$1"
    local TEST_NUMBER="$2"

    log_info "Testing edit_config.sh with ${VAR_NAME}..."

    # Test with valid phone number
    log_info "Testing with valid phone number: $TEST_NUMBER"
    if run_script "$VAR_NAME" "$TEST_NUMBER"; then
        log_success "Script executed successfully for $VAR_NAME"

        # Verify the change
        NEW_VALUE=$(run_cmd "grep '^${VAR_NAME}=' '$CONFIG_FILE' | cut -d'=' -f2 | tr -d '\"'")
        if [ "$NEW_VALUE" = "$TEST_NUMBER" ]; then
            log_success "${VAR_NAME} updated correctly to: $NEW_VALUE"
        else
            log_error "${VAR_NAME} value mismatch. Expected: $TEST_NUMBER, Got: $NEW_VALUE"
        fi
    else
        log_error "Script execution failed for $VAR_NAME"
    fi
}

# Test the edit_config.sh script with validation tests
test_script_validation() {
    log_info "Testing edit_config.sh validation..."

    # Test with invalid phone number (non-numeric)
    log_info "Testing with invalid phone number (non-numeric)..."
    if run_script "FIRST_NUMBER" "ABC123" 2>&1 | grep -q "ERROR.*Invalid"; then
        log_success "Script correctly rejected non-numeric input"
    else
        log_warn "Script did not properly validate non-numeric input"
    fi

    # Test with phone number too long (>30 digits)
    log_info "Testing with phone number too long (31 digits)..."
    LONG_NUMBER="1234567890123456789012345678901"
    if run_script "FIRST_NUMBER" "$LONG_NUMBER" 2>&1 | grep -q "ERROR.*Invalid"; then
        log_success "Script correctly rejected phone number > 30 digits"
    else
        log_warn "Script did not properly validate phone number length"
    fi

    # Test with empty phone number
    log_info "Testing with empty phone number..."
    if run_script "FIRST_NUMBER" "" 2>&1 | grep -q "ERROR"; then
        log_success "Script correctly rejected empty input"
    else
        log_warn "Script did not properly validate empty input"
    fi

    # Test with invalid config variable name
    log_info "Testing with invalid config variable name..."
    if run_script "INVALID VAR" "5551234567" 2>&1 | grep -q "ERROR.*Invalid"; then
        log_success "Script correctly rejected invalid variable name"
    else
        log_warn "Script did not properly validate variable name"
    fi
}

# Test phone numbers with special characters (* and #)
test_special_characters() {
    log_info "Testing phone numbers with special characters..."

    # Test with * prefix
    log_info "Testing phone number with * prefix: $TEST_PHONE_STAR"
    test_phone_number "FIRST_NUMBER" "$TEST_PHONE_STAR"

    # Test with # prefix
    log_info "Testing phone number with # prefix: $TEST_PHONE_HASH"
    test_phone_number "SECOND_NUMBER" "$TEST_PHONE_HASH"

    # Test with both * and # characters
    log_info "Testing phone number with both * and #: $TEST_PHONE_BOTH"
    test_phone_number "THIRD_NUMBER" "$TEST_PHONE_BOTH"

    # Additional comprehensive tests for local testing
    if [ "$IS_LOCAL" = true ]; then
        log_info "Running additional special character tests..."

        # Test with multiple special chars
        test_phone_number "FIRST_NUMBER" "**#123#456*789#"

        # Test with A-F characters (valid DTMF)
        test_phone_number "SECOND_NUMBER" "*#ABCDEF123"
    fi
}

# Restore original values
restore_original_values() {
    log_info "Restoring original phone number values..."

    if [ -n "$ORIGINAL_FIRST" ]; then
        log_info "Restoring FIRST_NUMBER: $ORIGINAL_FIRST"
        if run_script "FIRST_NUMBER" "$ORIGINAL_FIRST"; then
            log_success "FIRST_NUMBER restored"
        else
            log_error "Failed to restore FIRST_NUMBER"
        fi
    fi

    if [ -n "$ORIGINAL_SECOND" ]; then
        log_info "Restoring SECOND_NUMBER: $ORIGINAL_SECOND"
        if run_script "SECOND_NUMBER" "$ORIGINAL_SECOND"; then
            log_success "SECOND_NUMBER restored"
        else
            log_error "Failed to restore SECOND_NUMBER"
        fi
    fi

    if [ -n "$ORIGINAL_THIRD" ]; then
        log_info "Restoring THIRD_NUMBER: $ORIGINAL_THIRD"
        if run_script "THIRD_NUMBER" "$ORIGINAL_THIRD"; then
            log_success "THIRD_NUMBER restored"
        else
            log_error "Failed to restore THIRD_NUMBER"
        fi
    fi
}

# Check Asterisk configuration
test_asterisk_config() {
    if [ "$IS_LOCAL" = true ]; then
        log_info "Skipping Asterisk configuration checks for local testing"
        return 0
    fi

    log_info "Checking Asterisk configuration files..."

    # Check if confbridge.conf has all menu options
    log_info "Checking confbridge.conf for 01# menu entry..."
    if run_cmd "grep -q '^01#=dialplan_exec' /etc/asterisk/confbridge.conf"; then
        log_success "confbridge.conf has 01# menu entry"
    else
        log_error "confbridge.conf missing 01# menu entry"
    fi

    log_info "Checking confbridge.conf for 02# menu entry..."
    if run_cmd "grep -q '^02#=dialplan_exec' /etc/asterisk/confbridge.conf"; then
        log_success "confbridge.conf has 02# menu entry"
    else
        log_error "confbridge.conf missing 02# menu entry"
    fi

    log_info "Checking confbridge.conf for 03# menu entry..."
    if run_cmd "grep -q '^03#=dialplan_exec' /etc/asterisk/confbridge.conf"; then
        log_success "confbridge.conf has 03# menu entry"
    else
        log_warn "confbridge.conf missing 03# menu entry (optional)"
    fi

    # Check if extensions.conf has the phone editing extensions
    log_info "Checking extensions.conf for edit phone extensions..."
    if run_cmd "grep -q 'edit_primary_phone' /etc/asterisk/extensions.conf"; then
        log_success "extensions.conf has edit_primary_phone extension"
    else
        log_error "extensions.conf missing edit_primary_phone extension"
    fi

    if run_cmd "grep -q 'edit_second_phone' /etc/asterisk/extensions.conf"; then
        log_success "extensions.conf has edit_second_phone extension"
    else
        log_error "extensions.conf missing edit_second_phone extension"
    fi

    if run_cmd "grep -q 'edit_third_phone' /etc/asterisk/extensions.conf"; then
        log_success "extensions.conf has edit_third_phone extension"
    else
        log_warn "extensions.conf missing edit_third_phone extension (optional)"
    fi

    # Check if Asterisk is running
    log_info "Checking if Asterisk is running..."
    if run_cmd "pgrep -x asterisk > /dev/null"; then
        log_success "Asterisk is running"
    else
        log_error "Asterisk is not running"
    fi
}

# Manual test instructions for baresip
print_manual_test_instructions() {
    echo ""
    echo "=========================================================================="
    echo "MANUAL TEST INSTRUCTIONS - Using baresip"
    echo "=========================================================================="
    echo ""
    echo "1. SSH into the target system:"
    echo -e "   ${YELLOW}ssh $TARGET_HOST${NC}"
    echo ""
    echo "2. Start baresip as admin extension 201:"
    echo -e "   ${YELLOW}baresip sip:201@localhost${NC}"
    echo ""
    echo "3. From baresip, dial the conference:"
    echo -e "   ${YELLOW}/dial 9877${NC}"
    echo "   (This joins as admin with menu access)"
    echo ""
    echo "4. Test DTMF sequences:"
    echo ""
    echo "   FIRST_NUMBER (01#):"
    echo -e "   - Press: ${YELLOW}01#${NC}"
    echo -e "   - Enter test number: ${YELLOW}5551234567${NC}"
    echo -e "   - Verify: ${YELLOW}ssh $TARGET_HOST 'grep FIRST_NUMBER $CONFIG_FILE'${NC}"
    echo ""
    echo "   SECOND_NUMBER (02#):"
    echo -e "   - Press: ${YELLOW}02#${NC}"
    echo -e "   - Enter test number: ${YELLOW}5552345678${NC}"
    echo -e "   - Verify: ${YELLOW}ssh $TARGET_HOST 'grep SECOND_NUMBER $CONFIG_FILE'${NC}"
    echo ""
    echo "   THIRD_NUMBER (03#):"
    echo -e "   - Press: ${YELLOW}03#${NC}"
    echo -e "   - Enter test number: ${YELLOW}5553456789${NC}"
    echo -e "   - Verify: ${YELLOW}ssh $TARGET_HOST 'grep THIRD_NUMBER $CONFIG_FILE'${NC}"
    echo ""
    echo "5. Test playback (01*, 02*, 03*):"
    echo -e "   - Press ${YELLOW}01*${NC} to hear FIRST_NUMBER read digit-by-digit"
    echo -e "   - Press ${YELLOW}02*${NC} to hear SECOND_NUMBER read digit-by-digit"
    echo -e "   - Press ${YELLOW}03*${NC} to hear THIRD_NUMBER read digit-by-digit"
    echo ""
    echo "6. Exit baresip:"
    echo -e "   ${YELLOW}/quit${NC}"
    echo ""
    echo "=========================================================================="
    echo ""
}

# Check if backups are being created
test_backup_functionality() {
    log_info "Checking backup functionality..."

    BACKUP_COUNT=$(run_cmd "ls /mnt/data/backups/K3_config_settings_*.bak 2>/dev/null | wc -l")

    if [ "$BACKUP_COUNT" -gt 0 ]; then
        log_success "Found $BACKUP_COUNT backup file(s)"

        # Show the most recent backup
        LATEST_BACKUP=$(run_cmd "ls -t /mnt/data/backups/K3_config_settings_*.bak 2>/dev/null | head -n1")
        log_info "Latest backup: $LATEST_BACKUP"
    else
        log_warn "No backup files found (they may not have been created yet)"
    fi
}

# Main test execution
main() {
    echo ""
    echo "=========================================================================="
    echo "  TEST: Edit Phone Numbers Feature (01#, 02#, 03# DTMF)"
    echo "=========================================================================="
    echo ""

    if [ "$IS_LOCAL" = true ]; then
        log_info "Running tests locally"
        log_info "Config file: $CONFIG_FILE"
        log_info "Script path: $SCRIPT_PATH"
    else
        log_info "Running tests remotely on $TARGET_HOST"
        log_info "Config file: $CONFIG_FILE"
        log_info "Script path: $SCRIPT_PATH"
    fi
    echo ""

    # Setup local test environment if needed
    setup_local_test

    # Pre-flight checks
    if ! test_ssh_connection; then
        log_error "Cannot proceed without SSH connection"
        cleanup_local_test
        exit 1
    fi

    # Get original values (don't fail if they don't exist)
    get_current_phone_numbers || true

    # Run tests
    test_asterisk_config

    # Test each phone number
    test_phone_number "FIRST_NUMBER" "$TEST_PHONE_NUMBER_1"
    test_phone_number "SECOND_NUMBER" "$TEST_PHONE_NUMBER_2"
    test_phone_number "THIRD_NUMBER" "$TEST_PHONE_NUMBER_3"

    # Test special characters (* and #)
    test_special_characters

    # Test validation
    test_script_validation

    # Test backups
    test_backup_functionality

    # Restore original values
    restore_original_values

    # Print test summary
    echo ""
    echo "=========================================================================="
    echo "  TEST SUMMARY"
    echo "=========================================================================="
    echo -e "${GREEN}Passed: $TEST_PASSED${NC}"
    echo -e "${RED}Failed: $TEST_FAILED${NC}"
    echo ""

    # Print manual test instructions (skip for local tests)
    if [ "$IS_LOCAL" != true ]; then
        print_manual_test_instructions
    fi

    # Cleanup local test environment
    cleanup_local_test

    # Exit with appropriate code
    if [ $TEST_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main
