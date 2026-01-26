#!/bin/bash

# Kings3 Installation Script
# Configures the system for either Pool or Elevator mode

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# Parse command line arguments
CONFIG=""
UPDATE=false
INSTALL_PACKAGES=false
VERIFY_MODE=false
MD5_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --update)
            UPDATE=true
            shift
            ;;
        --package)
            INSTALL_PACKAGES=true
            shift
            ;;
        --verify)
            VERIFY_MODE=true
            if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
                MD5_FILE="$2"
                shift 2
            else
                shift
            fi
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --config <pool|elevator> [--update] [--package]"
            echo "       $0 --verify <md5-file>"
            exit 1
            ;;
    esac
done

# Validate that verification file is provided when using --verify
if [ "$VERIFY_MODE" = true ] && [ -z "$MD5_FILE" ]; then
    echo "Error: --verify requires a verification file to be specified"
    echo "Usage: $0 --verify <md5-file>"
    exit 1
fi

install_common_snd_files() {
    echo "Installing common sound files for dtmf functionality..."
    mkdir -p /usr/local/share/asterisk/sounds/ENU
    cp -r /mnt/data/sounds/ENU/* /usr/local/share/asterisk/sounds/ENU/.
    echo "Finished installing common sound files."
}

# Verify /mnt/data/sounds directory contains only expected files
verify_sounds_directory() {
    local sounds_dir="/mnt/data/sounds"

    # Color codes
    local RED='\033[0;31m'
    local GREEN='\033[0;32m'
    local YELLOW='\033[1;33m'
    local NC='\033[0m'

    echo ""
    echo "=============================================="
    echo "Verifying /mnt/data/sounds directory..."
    echo "=============================================="
    echo ""

    # Expected sound files (excluding subdirectories)
    local -a expected_files=(
        "S0000302.wav"
        "S0000301.wav"
        "S0000305.wav"
        "ENU00456-48k.wav"
        "S0000303-48k.wav"
        "ENU00209-48k.wav"
        "S0000300.wav"
        "ENU00456.wav"
        "ENU00209.wav"
        "ENU00459.wav"
        "S0000304.wav"
        "ENU00439.wav"
        "ENU00012.wav"
        "S0000209.wav"
        "S0000303.wav"
    )

    # Check if sounds directory exists
    if [ ! -d "$sounds_dir" ]; then
        echo -e "${RED}Error: Sounds directory not found: $sounds_dir${NC}"
        return 1
    fi

    local missing_count=0
    local extra_count=0
    local found_count=0

    # Check for expected files
    echo "Checking for expected files:"
    for file in "${expected_files[@]}"; do
        if [ -f "$sounds_dir/$file" ]; then
            echo -e "${GREEN}[OK]${NC} $file"
            found_count=$((found_count + 1))
        else
            echo -e "${RED}[MISSING]${NC} $file"
            missing_count=$((missing_count + 1))
        fi
    done

    echo ""
    echo "Checking for unexpected files:"

    # Check for unexpected files (excluding directories and hidden files)
    local has_unexpected=false
    while IFS= read -r -d '' file; do
        local basename=$(basename "$file")
        # Skip if it's a directory
        [ -d "$file" ] && continue
        # Skip hidden files
        [[ "$basename" == .* ]] && continue

        # Check if file is in expected list
        local is_expected=false
        for expected in "${expected_files[@]}"; do
            if [ "$basename" == "$expected" ]; then
                is_expected=true
                break
            fi
        done

        if [ "$is_expected" = false ]; then
            echo -e "${YELLOW}[UNEXPECTED]${NC} $basename"
            has_unexpected=true
            extra_count=$((extra_count + 1))
        fi
    done < <(find "$sounds_dir" -maxdepth 1 -type f -print0)

    if [ "$has_unexpected" = false ]; then
        echo -e "${GREEN}No unexpected files found${NC}"
    fi

    echo ""
    echo "=============================================="
    echo "Sounds Directory Verification Summary"
    echo "=============================================="
    echo -e "Expected files:    ${#expected_files[@]}"
    echo -e "${GREEN}Found:             $found_count${NC}"
    echo -e "${RED}Missing:           $missing_count${NC}"
    echo -e "${YELLOW}Unexpected:        $extra_count${NC}"
    echo "=============================================="
    echo ""

    if [ $missing_count -gt 0 ] || [ $extra_count -gt 0 ]; then
        echo -e "${RED}Sounds directory verification FAILED!${NC}"
        return 1
    else
        echo -e "${GREEN}Sounds directory verification SUCCESSFUL!${NC}"
        return 0
    fi
}

# Verification function
verify_installation() {
    local md5_file="$1"
    local config_file="/mnt/data/K3_config_settings"

    # Color codes
    local RED='\033[0;31m'
    local GREEN='\033[0;32m'
    local YELLOW='\033[1;33m'
    local NC='\033[0m'

    # Counters
    local total_files=0
    local verified_files=0
    local failed_files=0
    local missing_files=0

    echo ""
    echo "=============================================="
    echo "Starting installation verification..."
    echo "MD5 file: $md5_file"
    echo "=============================================="
    echo ""

    # Check if MD5 file exists
    if [ ! -f "$md5_file" ]; then
        echo -e "${RED}Error: MD5 file not found: $md5_file${NC}"
        exit 1
    fi

    # Read HW_APP from config file
    local hw_app=""
    if [ -f "$config_file" ]; then
        hw_app=$(grep '^HW_APP=' "$config_file" | cut -d'"' -f2)
        echo -e "${GREEN}Installation type: $hw_app${NC}"
        echo ""
    else
        echo -e "${YELLOW}Warning: Config file not found: $config_file${NC}"
        echo -e "${YELLOW}Unable to determine installation type${NC}"
        echo ""
    fi

    # Arrays for failures
    local -a failed_list
    local -a missing_list

    # Process each line in MD5 file
    while IFS= read -r line; do
        local expected_md5=$(echo "$line" | awk '{print $1}')
        local filename=$(echo "$line" | awk '{$1=""; print $0}' | sed 's/^ *//')
        local installed_path=""

        # Map filename to installed location
        case "$filename" in
            *.py)
                installed_path="/mnt/data/$filename"
                ;;
            *.service)
                if [[ "$filename" == "pulseaudio.service" ]]; then
                    installed_path="/home/kuser/.config/systemd/user/$filename"
                elif [[ "$filename" == "switch_mon.service" ]]; then
                    # switch_mon.service is only used in Pool installations
                    if [[ "$hw_app" == "Pool" ]]; then
                        installed_path="/etc/systemd/system/$filename"
                    else
                        continue
                    fi
                else
                    installed_path="/etc/systemd/system/$filename"
                fi
                ;;
            *.timer)
                installed_path="/etc/systemd/system/$filename"
                ;;
            *.sh)
                installed_path="/mnt/data/$filename"
                ;;
            "K3_config_settings")
                installed_path="/mnt/data/$filename"
                ;;
            sounds/ENU/*)
                local sound_file="${filename#sounds/}"
                installed_path="/usr/local/share/asterisk/sounds/$sound_file"
                ;;
            sounds/*)
                # Skip root-level sound files - they should only be in /mnt/data/sounds
                # and are verified separately by verify_sounds_directory()
                continue
                ;;
            "99-ignore-modemmanager.rules")
                installed_path="/etc/udev/rules.d/$filename"
                ;;
            "daemon.conf")
                installed_path="/etc/pulse/$filename"
                ;;
            *.csv)
                installed_path="/mnt/data/$filename"
                ;;
            "imx8mm-venice-gw7xxx-0x-gpio.dtbo")
                installed_path="/mnt/data/$filename"
                ;;
            "microcom.alias"|"CHANGELOG.md")
                installed_path="/mnt/data/$filename"
                ;;
            "extensions.conf"|"confbridge.conf"|"pjsip.conf"|"modules.conf"|"ari.conf"|"http.conf")
                if [[ "$hw_app" == "Elevator" ]]; then
                    installed_path="/etc/asterisk/$filename"
                else
                    continue
                fi
                ;;
            "interfaces")
                if [[ "$hw_app" == "Elevator" ]]; then
                    installed_path="/etc/network/$filename"
                else
                    continue
                fi
                ;;
            "default.pa")
                if [[ "$hw_app" == "Elevator" ]]; then
                    installed_path="/etc/pulse/$filename"
                else
                    continue
                fi
                ;;
            "accounts"|"config")
                if [[ "$hw_app" == "Elevator" ]]; then
                    installed_path="/home/kuser/.baresip/$filename"
                else
                    continue
                fi
                ;;
            "voip_call_monitor_tcp.py"|"voip_call_monitor.service"|"voip_ari_conference.service"|"ari-mon-conf.py")
                if [[ "$hw_app" == "Elevator" ]]; then
                    if [[ "$filename" == *.py ]]; then
                        installed_path="/mnt/data/$filename"
                    else
                        installed_path="/etc/systemd/system/$filename"
                    fi
                else
                    continue
                fi
                ;;
            "site_store.py"|"site.pub"|"site_info")
                installed_path="/mnt/data/$filename"
                ;;
            "GW-Setup-V"*.md5|"kings3_install.sh")
                continue
                ;;
            *)
                continue
                ;;
        esac

        total_files=$((total_files + 1))

        # Check if file exists
        if [ ! -f "$installed_path" ]; then
            missing_files=$((missing_files + 1))
            missing_list+=("$filename -> $installed_path")
            echo -e "${RED}[MISSING]${NC} $filename"
            continue
        fi

        # Calculate and compare checksums
        local actual_md5=$(md5sum "$installed_path" | awk '{print $1}')
        if [ "$expected_md5" == "$actual_md5" ]; then
            verified_files=$((verified_files + 1))
            echo -e "${GREEN}[OK]${NC} $filename"
        else
            failed_files=$((failed_files + 1))
            failed_list+=("$filename -> $installed_path")
            echo -e "${RED}[FAIL]${NC} $filename (checksum mismatch)"
        fi
    done < "$md5_file"

    # Print summary
    echo ""
    echo "=============================================="
    echo "Verification Summary"
    echo "=============================================="
    echo -e "Total files checked:    $total_files"
    echo -e "${GREEN}Verified (OK):          $verified_files${NC}"
    echo -e "${RED}Failed (checksum):      $failed_files${NC}"
    echo -e "${RED}Missing (not found):    $missing_files${NC}"
    echo "=============================================="

    if [ $failed_files -gt 0 ]; then
        echo ""
        echo -e "${RED}Files with checksum mismatches:${NC}"
        for item in "${failed_list[@]}"; do
            echo "  - $item"
        done
    fi

    if [ $missing_files -gt 0 ]; then
        echo ""
        echo -e "${RED}Missing files:${NC}"
        for item in "${missing_list[@]}"; do
            echo "  - $item"
        done
    fi

    echo ""

    # Exit with appropriate code
    if [ $failed_files -gt 0 ] || [ $missing_files -gt 0 ]; then
        echo -e "${RED}Verification FAILED!${NC}"
        return 1
    else
        echo -e "${GREEN}Verification SUCCESSFUL! All files match.${NC}"
        return 0
    fi
}

# If verify mode, run verification and exit
if [ "$VERIFY_MODE" = true ]; then
    verify_installation "$MD5_FILE"
    install_result=$?

    verify_sounds_directory
    sounds_result=$?

    # Exit with failure if either verification failed
    if [ $install_result -ne 0 ] || [ $sounds_result -ne 0 ]; then
        echo ""
        echo -e "\033[0;31m================================\033[0m"
        echo -e "\033[0;31mOVERALL VERIFICATION FAILED!\033[0m"
        echo -e "\033[0;31m================================\033[0m"
        exit 1
    else
        echo ""
        echo -e "\033[0;32m================================\033[0m"
        echo -e "\033[0;32mOVERALL VERIFICATION PASSED!\033[0m"
        echo -e "\033[0;32m================================\033[0m"
        exit 0
    fi
fi

# Validate config parameter
if [ -z "$CONFIG" ]; then
    echo "Error: --config parameter is required"
    echo "Usage: $0 --config <pool|elevator> [--update] [--package]"
    echo "       $0 --verify <md5-file>"
    exit 1
fi

if [ "$CONFIG" != "pool" ] && [ "$CONFIG" != "elevator" ]; then
    echo "Error: --config must be either 'pool' or 'elevator'"
    echo "Usage: $0 --config <pool|elevator> [--update] [--package]"
    echo "       $0 --verify <md5-file>"
    exit 1
fi

echo ""
echo "=============================================="
echo ""
echo "Starting Kings3 installation..."
echo "Configuration: $CONFIG"
echo "Update mode: $UPDATE"
echo "Install packages: $INSTALL_PACKAGES"
echo ""
echo "=============================================="

# Function to update config settings while preserving existing values
# Reads K3_config_settings.default and merges new settings into K3_config_settings
# Preserves all existing values in K3_config_settings, adds missing settings from .default
# Always preserves APP version from K3_config_settings
update_config_settings() {
    local config_file="/mnt/data/K3_config_settings"
    local default_file="/mnt/data/K3_config_settings.default"
    local temp_file="/tmp/K3_config_settings.tmp"

    echo "Updating configuration settings..."

    # Check if both files exist
    if [ ! -f "$config_file" ]; then
        echo "Warning: $config_file not found, cannot update settings"
        return 1
    fi

    if [ ! -f "$default_file" ]; then
        echo "Warning: $default_file not found, cannot update settings"
        return 1
    fi

    # Create associative arrays to store settings
    declare -A existing_settings
    declare -A default_settings
    declare -A existing_comments

    # Read existing K3_config_settings file
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines
        if [ -z "$line" ]; then
            continue
        fi

        # Extract variable name and value (handle inline comments)
        if [[ $line =~ ^([A-Za-z_][A-Za-z0-9_]*)=\"([^\"]*)\"(.*)$ ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            local comment="${BASH_REMATCH[3]}"
            existing_settings["$var_name"]="$var_value"
            existing_comments["$var_name"]="$comment"
        fi
    done < "$config_file"

    # Read K3_config_settings.default file
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines
        if [ -z "$line" ]; then
            continue
        fi

        # Extract variable name and value (handle inline comments)
        if [[ $line =~ ^([A-Za-z_][A-Za-z0-9_]*)=\"([^\"]*)\"(.*)$ ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            local comment="${BASH_REMATCH[3]}"
            default_settings["$var_name"]="$var_value"

            # Store comment if not already in existing_comments
            if [ -z "${existing_comments[$var_name]}" ] && [ -n "$comment" ]; then
                existing_comments["$var_name"]="$comment"
            fi
        fi
    done < "$default_file"

    # Build the updated config file
    > "$temp_file"  # Clear temp file

    # Process all settings from default file (to maintain order)
    while IFS= read -r line || [ -n "$line" ]; do
        # Keep empty lines
        if [ -z "$line" ]; then
            echo "" >> "$temp_file"
            continue
        fi

        # Check if line is a variable assignment
        if [[ $line =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
            local var_name="${BASH_REMATCH[1]}"

            # Special case: Always use APP version from default config.
            # The APP variable must be updated to reflect the new version being installed.
            if [ "$var_name" = "APP" ]; then
                echo "$line" >> "$temp_file"
                echo "  - Updated APP to new version: ${default_settings[$var_name]}"
            # If setting exists in current config, use the existing value
            elif [ -n "${existing_settings[$var_name]+isset}" ]; then
                echo "${var_name}=\"${existing_settings[$var_name]}\"${existing_comments[$var_name]}" >> "$temp_file"
            # If setting doesn't exist in current config, add it from default
            else
                echo "$line" >> "$temp_file"
                echo "  + Added new setting: $var_name=\"${default_settings[$var_name]}\""
            fi
        else
            # Keep comments and other lines as-is
            echo "$line" >> "$temp_file"
        fi
    done < "$default_file"

    # Check if there are any settings in existing config that are not in default
    # (These should be preserved at the end of the file)
    local added_extra=false
    for var_name in "${!existing_settings[@]}"; do
        if [ -z "${default_settings[$var_name]+isset}" ]; then
            if [ "$added_extra" = false ]; then
                echo "" >> "$temp_file"
                echo "# Additional settings from previous configuration" >> "$temp_file"
                added_extra=true
            fi
            echo "${var_name}=\"${existing_settings[$var_name]}\"${existing_comments[$var_name]}" >> "$temp_file"
            echo "  - Preserved legacy setting: $var_name"
        fi
    done

    # Replace the original config file with updated version
    mv "$temp_file" "$config_file"
    echo "Configuration settings updated successfully!"
    echo ""

    chown asterisk:asterisk "$config_file"
}

# Function to install or update services
# Usage: install_or_update_services service1 [service2 ...]
# Example: install_or_update_services switch_mon.service manage_modem.service
install_or_update_services() {
    local services=("$@")

    for service_name in "${services[@]}"; do
        local source_path="/mnt/data/$service_name"
        local start_time=$(date +%s.%N)

        echo "Processing service: $service_name"

        # Copy service file to systemd directory
        local copy_start=$(date +%s.%N)
        cp "$source_path" /etc/systemd/system/"$service_name"
        local copy_end=$(date +%s.%N)
        local copy_time=$(echo "$copy_end - $copy_start" | bc)
        echo "  - Copy completed in ${copy_time}s"

        # Reload systemd daemon
        local reload_start=$(date +%s.%N)
        systemctl daemon-reload
        local reload_end=$(date +%s.%N)
        local reload_time=$(echo "$reload_end - $reload_start" | bc)
        echo "  - Daemon reload completed in ${reload_time}s"

        if [ "$UPDATE" = true ]; then
            # Check if service is currently enabled
            if systemctl is-enabled "$service_name" &>/dev/null; then
                local restart_start=$(date +%s.%N)
                systemctl restart "$service_name"
                local restart_end=$(date +%s.%N)
                local restart_time=$(echo "$restart_end - $restart_start" | bc)
                echo "  - Service restart completed in ${restart_time}s"
            else
                # Service not enabled yet (new service on update)
                local enable_start=$(date +%s.%N)
                systemctl enable "$service_name"
                systemctl start "$service_name"
                local enable_end=$(date +%s.%N)
                local enable_time=$(echo "$enable_end - $enable_start" | bc)
                echo "  - Service enable+start completed in ${enable_time}s"
            fi
        else
            local enable_start=$(date +%s.%N)
            systemctl enable "$service_name"
            systemctl start "$service_name"
            local enable_end=$(date +%s.%N)
            local enable_time=$(echo "$enable_end - $enable_start" | bc)
            echo "  - Service enable+start completed in ${enable_time}s"
        fi

        local end_time=$(date +%s.%N)
        local total_time=$(echo "$end_time - $start_time" | bc)
        echo "  ✓ Total time for $service_name: ${total_time}s"
        echo ""
    done
}

# In both types of configurations, ensure the following packages are installed.
if [ "$INSTALL_PACKAGES" = true ]; then
    echo "Installing packages..."
    apt-get install -y  python3-serial microcom pulseaudio btop \
        python3-aiohttp python3-dotenv lm-sensors alsa-utils bc


    # Additional packages for elevator configuration.
    if [ "$CONFIG" == "elevator" ]; then
        apt-get install -y baresip asterisk
    fi
    echo "Package installation complete."
else
    echo "Skipping package installation (use --package to install packages)"
fi

install_common_snd_files

# Pool configuration (based on config_sys.sh)
if [ "$CONFIG" == "pool" ]; then
    echo "Configuring for Pool mode..."

    # Update config settings if in update mode
    if [ "$UPDATE" = true ]; then
        update_config_settings
    fi

    # Set audio routing to ON for pool mode
    sed -i 's/^ENABLE_AUDIO_ROUTING=.*/ENABLE_AUDIO_ROUTING="ON"/' /mnt/data/K3_config_settings
    sed -i 's/^HW_APP=.*/HW_APP="Pool"/' /mnt/data/K3_config_settings

    cp /mnt/data/99-ignore-modemmanager.rules  /etc/udev/rules.d/99-ignore-modemmanager.rules

    cp /mnt/data/daemon.conf /etc/pulse/daemon.conf

    mkdir -p /home/kuser/.config/systemd/user
    cp /mnt/data/pulseaudio.service /home/kuser/.config/systemd/user/pulseaudio.service
    # Everything under kuser needs to be owned by kuser.
    # IF not when doing the "systemctl --user enable pulseaudio.service" it will fail.
    chown -R kuser:kuser /home/kuser/.config

    touch /mnt/data/calls.log
    chmod ugo+w /mnt/data/calls.log

    loginctl enable-linger kuser

    # Copy get_sensor_data.service separately (it's used by the timer)
    cp /mnt/data/get_sensor_data.service /etc/systemd/system/

    install_or_update_services switch_mon.service \
        manage_modem.service \
        events_monitor.service \
        get_sensor_data.timer

    echo "Pool configuration complete!"
    echo "Note: You must run 'systemctl --user enable pulseaudio.service' as kuser"

# Elevator configuration (based on voip_config.sh)
elif [ "$CONFIG" == "elevator" ]; then
    echo "Configuring for Elevator mode..."

    # Update config settings if in update mode
    if [ "$UPDATE" = true ]; then
        update_config_settings
    fi

    # Set audio routing to OFF for elevator mode
    sed -i 's/^ENABLE_AUDIO_ROUTING=.*/ENABLE_AUDIO_ROUTING="OFF"/' /mnt/data/K3_config_settings
    sed -i 's/^HW_APP=.*/HW_APP="Elevator"/' /mnt/data/K3_config_settings

    cp /mnt/data/extensions.conf /etc/asterisk/extensions.conf
    cp /mnt/data/confbridge.conf /etc/asterisk/confbridge.conf
    cp /mnt/data/pjsip.conf /etc/asterisk/pjsip.conf
    cp /mnt/data/modules.conf /etc/asterisk/modules.conf
    cp /mnt/data/ari.conf /etc/asterisk/ari.conf
    cp /mnt/data/http.conf /etc/asterisk/http.conf
    chown asterisk:asterisk /etc/asterisk/extensions.conf  \
         /etc/asterisk/pjsip.conf /etc/asterisk/modules.conf \
         /etc/asterisk/confbridge.conf /etc/asterisk/ari.conf \
         /etc/asterisk/http.conf


    # Create call log file and change ownership.
    touch /mnt/data/calls.log
    chown kuser:kuser /mnt/data/calls.log

    # Baresip setup
    mkdir -p /home/kuser/.baresip


    cp /mnt/data/accounts /home/kuser/.baresip/accounts
    cp /mnt/data/config /home/kuser/.baresip/config
    chown -R kuser:kuser /home/kuser/.baresip

    # Network interfaces setup
    cp /mnt/data/interfaces /etc/network/interfaces

    # PulseAudio setup
    cp /mnt/data/default.pa /etc/pulse/default.pa
    cp /mnt/data/daemon.conf /etc/pulse/daemon.conf

    mkdir -p /home/kuser/.config/systemd/user
    cp /mnt/data/pulseaudio.service /home/kuser/.config/systemd/user/pulseaudio.service
    # Everything under kuser needs to be owned by kuser.
    # IF not when doing the "systemctl --user enable pulseaudio.service" it will fail.
    chown -R kuser:kuser /home/kuser/.config


    # Turn off the modem manager attempting to manage the cellular modem.
    cp /mnt/data/99-ignore-modemmanager.rules  /etc/udev/rules.d/99-ignore-modemmanager.rules

    # Copy get_sensor_data.service separately (it's used by the timer)
    cp /mnt/data/get_sensor_data.service /etc/systemd/system/

    # Install or update all services
    install_or_update_services \
        voip_call_monitor.service \
        voip_ari_conference.service \
        manage_modem.service \
        events_monitor.service \
        get_sensor_data.timer \
        set-governor.service

    #systemctl status get_sensor_data.timer
    #systemctl list-timers get_sensor_data.timer

    echo "Elevator configuration complete!"
fi

echo ""
echo "Kings3 installation finished successfully!"
