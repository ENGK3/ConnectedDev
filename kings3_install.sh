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
            MD5_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --config <pool|elevator> [--update] [--package]"
            echo "       $0 --verify <md5-file>"
            exit 1
            ;;
    esac
done

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
            sounds/*)
                local sound_file="${filename#sounds/}"
                installed_path="/usr/local/share/asterisk/sounds/$sound_file"
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
        exit 1
    else
        echo -e "${GREEN}Verification SUCCESSFUL! All files match.${NC}"
        exit 0
    fi
}

# If verify mode, run verification and exit
if [ "$VERIFY_MODE" = true ]; then
    verify_installation "$MD5_FILE"
    exit $?
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

install_common_snd_files() {
    echo "Installing common sound files for dtmf functionality..."
    mkdir -p /usr/local/share/asterisk/sounds/ENU
    cp -r /mnt/data/sounds/ENU/* /usr/local/share/asterisk/sounds/ENU/.
    echo "Finished installing common sound files."
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

install_common_snd_files()

# Pool configuration (based on config_sys.sh)
if [ "$CONFIG" == "pool" ]; then
    echo "Configuring for Pool mode..."

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
        get_sensor_data.timer \
        set-governor.service

    #systemctl status get_sensor_data.timer
    #systemctl list-timers get_sensor_data.timer

    echo "Elevator configuration complete!"
fi

echo ""
echo "Kings3 installation finished successfully!"
