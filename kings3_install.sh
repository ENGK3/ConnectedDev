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
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --config <pool|elevator> [--update]"
            exit 1
            ;;
    esac
done

# Validate config parameter
if [ -z "$CONFIG" ]; then
    echo "Error: --config parameter is required"
    echo "Usage: $0 --config <pool|elevator> [--update]"
    exit 1
fi

if [ "$CONFIG" != "pool" ] && [ "$CONFIG" != "elevator" ]; then
    echo "Error: --config must be either 'pool' or 'elevator'"
    echo "Usage: $0 --config <pool|elevator> [--update]"
    exit 1
fi

echo ""
echo "=============================================="
echo ""
echo "Starting Kings3 installation..."
echo "Configuration: $CONFIG"
echo "Update mode: $UPDATE"
echo ""
echo "=============================================="

# Function to install or update services
# Usage: install_or_update_services service1 [service2 ...]
# Example: install_or_update_services switch_mon.service manage_modem.service
install_or_update_services() {
    local services=("$@")

    for service_name in "${services[@]}"; do
        local source_path="/mnt/data/$service_name"

        echo "Processing service: $service_name"

        # Copy service file to systemd directory
        cp "$source_path" /etc/systemd/system/"$service_name"

        systemctl daemon-reload

        if [ "$UPDATE" = true ]; then
            # Check if service is currently enabled
            if systemctl is-enabled "$service_name" &>/dev/null; then
                systemctl restart "$service_name"
            else
                # Service not enabled yet (new service on update)
                systemctl enable "$service_name"
                systemctl start "$service_name"
            fi
        else
            systemctl enable "$service_name"
            systemctl start "$service_name"
        fi
    done
}

# In both types of configurations, ensure the following packages are installed.

apt-get install -y  python3-serial microcom pulseaudio btop \
    python3-aiohttp python3-dotenv lm-sensors

# Additional packages for elevator configuration.
if [ "$CONFIG" == "elevator" ]; then
    apt-get install -y baresip asterisk
fi

# Pool configuration (based on config_sys.sh)
if [ "$CONFIG" == "pool" ]; then
    echo "Configuring for Pool mode..."

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

    install_or_update_services switch_mon.service  manage_modem.service

    echo "Pool configuration complete!"
    echo "Note: You must run 'systemctl --user enable pulseaudio.service' as kuser"

# Elevator configuration (based on voip_config.sh)
elif [ "$CONFIG" == "elevator" ]; then
    echo "Configuring for Elevator mode..."

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
