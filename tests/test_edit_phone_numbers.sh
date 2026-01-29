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
#   - SSH access to target host
#   - baresip client available on the target
#   - Asterisk running with the new configuration
#   - Admin extension (200 or 201) configured
#
# Usage: ./test_edit_phone_numbers.sh [TARGET_HOST]
#   TARGET_HOST: SSH target (e.g., root@GWorks2) [default: root@GWorks2]
##############################################################################

set -e

# Parse command line arguments
TARGET_HOST="${1:-root@GWorks2}"
CONFIG_FILE="/mnt/data/K3_config_settings"
TEST_PHONE_NUMBER_1="5551234567"
TEST_PHONE_NUMBER_2="5552345678"
TEST_PHONE_NUMBER_3="5553456789"
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

    ORIGINAL_FIRST=$(ssh "$TARGET_HOST" "grep '^FIRST_NUMBER=' '$CONFIG_FILE' 2>/dev/null | cut -d'=' -f2 | tr -d '\"'")
    ORIGINAL_SECOND=$(ssh "$TARGET_HOST" "grep '^SECOND_NUMBER=' '$CONFIG_FILE' 2>/dev/null | cut -d'=' -f2 | tr -d '\"'")
    ORIGINAL_THIRD=$(ssh "$TARGET_HOST" "grep '^THIRD_NUMBER=' '$CONFIG_FILE' 2>/dev/null | cut -d'=' -f2 | tr -d '\"'")

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
    if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh $VAR_NAME $TEST_NUMBER"; then
        log_success "Script executed successfully for $VAR_NAME"

        # Verify the change
        NEW_VALUE=$(ssh "$TARGET_HOST" "grep '^${VAR_NAME}=' '$CONFIG_FILE' | cut -d'=' -f2 | tr -d '\"'")
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
    if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh FIRST_NUMBER ABC123" 2>&1 | grep -q "ERROR.*Invalid"; then
        log_success "Script correctly rejected non-numeric input"
    else
        log_warn "Script did not properly validate non-numeric input"
    fi

    # Test with phone number too long (>30 digits)
    log_info "Testing with phone number too long (31 digits)..."
    LONG_NUMBER="1234567890123456789012345678901"
    if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh FIRST_NUMBER $LONG_NUMBER" 2>&1 | grep -q "ERROR.*Invalid"; then
        log_success "Script correctly rejected phone number > 30 digits"
    else
        log_warn "Script did not properly validate phone number length"
    fi

    # Test with empty phone number
    log_info "Testing with empty phone number..."
    if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh FIRST_NUMBER ''" 2>&1 | grep -q "ERROR"; then
        log_success "Script correctly rejected empty input"
    else
        log_warn "Script did not properly validate empty input"
    fi

    # Test with invalid config variable name
    log_info "Testing with invalid config variable name..."
    if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh 'INVALID VAR' 5551234567" 2>&1 | grep -q "ERROR.*Invalid"; then
        log_success "Script correctly rejected invalid variable name"
    else
        log_warn "Script did not properly validate variable name"
    fi
}

# Restore original values
restore_original_values() {
    log_info "Restoring original phone number values..."

    if [ -n "$ORIGINAL_FIRST" ]; then
        log_info "Restoring FIRST_NUMBER: $ORIGINAL_FIRST"
        if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh FIRST_NUMBER $ORIGINAL_FIRST"; then
            log_success "FIRST_NUMBER restored"
        else
            log_error "Failed to restore FIRST_NUMBER"
        fi
    fi

    if [ -n "$ORIGINAL_SECOND" ]; then
        log_info "Restoring SECOND_NUMBER: $ORIGINAL_SECOND"
        if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh SECOND_NUMBER $ORIGINAL_SECOND"; then
            log_success "SECOND_NUMBER restored"
        else
            log_error "Failed to restore SECOND_NUMBER"
        fi
    fi

    if [ -n "$ORIGINAL_THIRD" ]; then
        log_info "Restoring THIRD_NUMBER: $ORIGINAL_THIRD"
        if ssh "$TARGET_HOST" "/mnt/data/edit_config.sh THIRD_NUMBER $ORIGINAL_THIRD"; then
            log_success "THIRD_NUMBER restored"
        else
            log_error "Failed to restore THIRD_NUMBER"
        fi
    fi
}

# Check Asterisk configuration
test_asterisk_config() {
    log_info "Checking Asterisk configuration files..."

    # Check if confbridge.conf has all menu options
    log_info "Checking confbridge.conf for 01# menu entry..."
    if ssh "$TARGET_HOST" "grep -q '^01#=dialplan_exec' /etc/asterisk/confbridge.conf"; then
        log_success "confbridge.conf has 01# menu entry"
    else
        log_error "confbridge.conf missing 01# menu entry"
    fi

    log_info "Checking confbridge.conf for 02# menu entry..."
    if ssh "$TARGET_HOST" "grep -q '^02#=dialplan_exec' /etc/asterisk/confbridge.conf"; then
        log_success "confbridge.conf has 02# menu entry"
    else
        log_error "confbridge.conf missing 02# menu entry"
    fi

    log_info "Checking confbridge.conf for 03# menu entry..."
    if ssh "$TARGET_HOST" "grep -q '^03#=dialplan_exec' /etc/asterisk/confbridge.conf"; then
        log_success "confbridge.conf has 03# menu entry"
    else
        log_warn "confbridge.conf missing 03# menu entry (optional)"
    fi

    # Check if extensions.conf has the phone editing extensions
    log_info "Checking extensions.conf for edit phone extensions..."
    if ssh "$TARGET_HOST" "grep -q 'edit_primary_phone' /etc/asterisk/extensions.conf"; then
        log_success "extensions.conf has edit_primary_phone extension"
    else
        log_error "extensions.conf missing edit_primary_phone extension"
    fi

    if ssh "$TARGET_HOST" "grep -q 'edit_second_phone' /etc/asterisk/extensions.conf"; then
        log_success "extensions.conf has edit_second_phone extension"
    else
        log_error "extensions.conf missing edit_second_phone extension"
    fi

    if ssh "$TARGET_HOST" "grep -q 'edit_third_phone' /etc/asterisk/extensions.conf"; then
        log_success "extensions.conf has edit_third_phone extension"
    else
        log_warn "extensions.conf missing edit_third_phone extension (optional)"
    fi

    # Check if Asterisk is running
    log_info "Checking if Asterisk is running..."
    if ssh "$TARGET_HOST" "pgrep -x asterisk > /dev/null"; then
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

    BACKUP_COUNT=$(ssh "$TARGET_HOST" "ls /mnt/data/backups/K3_config_settings_*.bak 2>/dev/null | wc -l")

    if [ "$BACKUP_COUNT" -gt 0 ]; then
        log_success "Found $BACKUP_COUNT backup file(s)"

        # Show the most recent backup
        LATEST_BACKUP=$(ssh "$TARGET_HOST" "ls -t /mnt/data/backups/K3_config_settings_*.bak 2>/dev/null | head -n1")
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

    # Pre-flight checks
    if ! test_ssh_connection; then
        log_error "Cannot proceed without SSH connection"
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

    # Print manual test instructions
    print_manual_test_instructions

    # Exit with appropriate code
    if [ $TEST_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main
