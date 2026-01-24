#!/bin/bash

# verify_installation.sh
# Verifies installed files on the target system against checksums in GW-Setup-V<version>.md5

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TOTAL_FILES=0
VERIFIED_FILES=0
FAILED_FILES=0
MISSING_FILES=0

# Default paths
MD5_FILE=""
CONFIG_FILE="/mnt/data/K3_config_settings"
VERBOSE=false

# Function to show usage
usage() {
    echo "Usage: $0 --md5 <path-to-md5-file> [--config <config-file>] [--verbose]"
    echo ""
    echo "Options:"
    echo "  --md5 <file>      Path to GW-Setup-V<version>.md5 checksum file (required)"
    echo "  --config <file>   Path to K3_config_settings file (default: /mnt/data/K3_config_settings)"
    echo "  --verbose         Show detailed output for each file"
    echo ""
    echo "Examples:"
    echo "  $0 --md5 GW-Setup-V00.03.04.md5"
    echo "  $0 --md5 /tmp/GW-Setup-V00.03.04.md5 --verbose"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --md5)
            MD5_FILE="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$MD5_FILE" ]; then
    echo -e "${RED}Error: --md5 parameter is required${NC}"
    usage
fi

if [ ! -f "$MD5_FILE" ]; then
    echo -e "${RED}Error: MD5 file not found: $MD5_FILE${NC}"
    exit 1
fi

# Read HW_APP from config file to determine installation type
HW_APP=""
if [ -f "$CONFIG_FILE" ]; then
    # Extract HW_APP value from config file
    HW_APP=$(grep '^HW_APP=' "$CONFIG_FILE" | cut -d'"' -f2)
    echo -e "${GREEN}Installation type: $HW_APP${NC}"
else
    echo -e "${YELLOW}Warning: Config file not found: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Unable to determine installation type (Pool or Elevator)${NC}"
fi

echo ""
echo "=============================================="
echo "Starting installation verification..."
echo "MD5 file: $MD5_FILE"
echo "Config file: $CONFIG_FILE"
echo "=============================================="
echo ""

# Function to get installed file path based on filename
get_installed_path() {
    local filename="$1"

    # Map filenames to their installed locations based on kings3_install.sh
    case "$filename" in
        # Python scripts to /mnt/data
        *.py)
            echo "/mnt/data/$filename"
            ;;
        # Service files to /etc/systemd/system
        *.service)
            if [[ "$filename" == "pulseaudio.service" ]]; then
                echo "/home/kuser/.config/systemd/user/$filename"
            else
                echo "/etc/systemd/system/$filename"
            fi
            ;;
        # Timer files to /etc/systemd/system
        *.timer)
            echo "/etc/systemd/system/$filename"
            ;;
        # Shell scripts to /mnt/data
        *.sh)
            if [[ "$filename" == "edit_config.sh" ]]; then
                echo "/mnt/data/$filename"
            else
                echo "/mnt/data/$filename"
            fi
            ;;
        # K3_config_settings
        "K3_config_settings")
            echo "/mnt/data/$filename"
            ;;
        # Sound files
        sounds/*)
            local sound_file="${filename#sounds/}"
            echo "/usr/local/share/asterisk/sounds/$sound_file"
            ;;
        # udev rules
        "99-ignore-modemmanager.rules")
            echo "/etc/udev/rules.d/$filename"
            ;;
        # PulseAudio daemon.conf
        "daemon.conf")
            echo "/etc/pulse/$filename"
            ;;
        # CSV lookup tables
        *.csv)
            echo "/mnt/data/$filename"
            ;;
        # Device tree overlay
        "imx8mm-venice-gw7xxx-0x-gpio.dtbo")
            echo "/mnt/data/$filename"
            ;;
        # microcom alias
        "microcom.alias")
            echo "/mnt/data/$filename"
            ;;
        # CHANGELOG
        "CHANGELOG.md")
            echo "/mnt/data/$filename"
            ;;
        # Elevator-specific files (only check if HW_APP="Elevator")
        "extensions.conf"|"confbridge.conf"|"pjsip.conf"|"modules.conf"|"ari.conf"|"http.conf")
            if [[ "$HW_APP" == "Elevator" ]]; then
                echo "/etc/asterisk/$filename"
            else
                echo "SKIP"
            fi
            ;;
        "interfaces")
            if [[ "$HW_APP" == "Elevator" ]]; then
                echo "/etc/network/$filename"
            else
                echo "SKIP"
            fi
            ;;
        "default.pa")
            if [[ "$HW_APP" == "Elevator" ]]; then
                echo "/etc/pulse/$filename"
            else
                echo "SKIP"
            fi
            ;;
        "accounts"|"config")
            if [[ "$HW_APP" == "Elevator" ]]; then
                echo "/home/kuser/.baresip/$filename"
            else
                echo "SKIP"
            fi
            ;;
        "voip_call_monitor_tcp.py"|"voip_call_monitor.service"|"voip_ari_conference.service"|"ari-mon-conf.py")
            if [[ "$HW_APP" == "Elevator" ]]; then
                if [[ "$filename" == *.py ]]; then
                    echo "/mnt/data/$filename"
                else
                    echo "/etc/systemd/system/$filename"
                fi
            else
                echo "SKIP"
            fi
            ;;
        # Common metadata files
        "site_store.py"|"site.pub"|"site_info")
            echo "/mnt/data/$filename"
            ;;
        # The md5 file itself and install script
        "GW-Setup-V"*.md5|"kings3_install.sh")
            echo "SKIP"
            ;;
        *)
            echo "UNKNOWN"
            ;;
    esac
}

# Array to hold failed verifications
declare -a FAILED_LIST
declare -a MISSING_LIST

# Process each line in the MD5 file
while IFS= read -r line; do
    # Extract checksum and filename
    expected_md5=$(echo "$line" | awk '{print $1}')
    filename=$(echo "$line" | awk '{$1=""; print $0}' | sed 's/^ *//')

    # Get the installed path for this file
    installed_path=$(get_installed_path "$filename")

    # Skip if this file should not be checked
    if [[ "$installed_path" == "SKIP" ]]; then
        if $VERBOSE; then
            echo -e "${YELLOW}[SKIP]${NC} $filename (not applicable for $HW_APP configuration)"
        fi
        continue
    fi

    if [[ "$installed_path" == "UNKNOWN" ]]; then
        if $VERBOSE; then
            echo -e "${YELLOW}[UNKNOWN]${NC} $filename (unknown installation path)"
        fi
        continue
    fi

    TOTAL_FILES=$((TOTAL_FILES + 1))

    # Check if file exists
    if [ ! -f "$installed_path" ]; then
        MISSING_FILES=$((MISSING_FILES + 1))
        MISSING_LIST+=("$filename -> $installed_path")
        if $VERBOSE; then
            echo -e "${RED}[MISSING]${NC} $filename"
            echo -e "          Expected at: $installed_path"
        fi
        continue
    fi

    # Calculate MD5 checksum of installed file
    actual_md5=$(md5sum "$installed_path" | awk '{print $1}')

    # Compare checksums
    if [ "$expected_md5" == "$actual_md5" ]; then
        VERIFIED_FILES=$((VERIFIED_FILES + 1))
        if $VERBOSE; then
            echo -e "${GREEN}[OK]${NC} $filename"
        fi
    else
        FAILED_FILES=$((FAILED_FILES + 1))
        FAILED_LIST+=("$filename -> $installed_path")
        if $VERBOSE; then
            echo -e "${RED}[FAIL]${NC} $filename"
            echo -e "       Expected: $expected_md5"
            echo -e "       Got:      $actual_md5"
            echo -e "       Path:     $installed_path"
        fi
    fi

done < "$MD5_FILE"

# Print summary
echo ""
echo "=============================================="
echo "Verification Summary"
echo "=============================================="
echo -e "Total files checked:    $TOTAL_FILES"
echo -e "${GREEN}Verified (OK):          $VERIFIED_FILES${NC}"
echo -e "${RED}Failed (checksum):      $FAILED_FILES${NC}"
echo -e "${RED}Missing (not found):    $MISSING_FILES${NC}"
echo "=============================================="

# Show details of failures if not in verbose mode
if [ $FAILED_FILES -gt 0 ] && ! $VERBOSE; then
    echo ""
    echo -e "${RED}Files with checksum mismatches:${NC}"
    for item in "${FAILED_LIST[@]}"; do
        echo "  - $item"
    done
fi

if [ $MISSING_FILES -gt 0 ] && ! $VERBOSE; then
    echo ""
    echo -e "${RED}Missing files:${NC}"
    for item in "${MISSING_LIST[@]}"; do
        echo "  - $item"
    done
fi

echo ""

# Exit with appropriate code
if [ $FAILED_FILES -gt 0 ] || [ $MISSING_FILES -gt 0 ]; then
    echo -e "${RED}Verification FAILED!${NC}"
    exit 1
else
    echo -e "${GREEN}Verification SUCCESSFUL! All files match.${NC}"
    exit 0
fi
