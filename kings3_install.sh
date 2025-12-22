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
# Pool configuration (based on config_sys.sh)
if [ "$CONFIG" == "pool" ]; then
    echo "Configuring for Pool mode..."

    cp /mnt/data/99-ignore-modemmanager.rules  /etc/udev/rules.d/99-ignore-modemmanager.rules
    cp /mnt/data/switch_mon.service /etc/systemd/system/switch_mon.service

    cp /mnt/data/daemon.conf /etc/pulse/daemon.conf

    mkdir -p /home/kuser/.config/systemd/user
    cp /mnt/data/pulseaudio.service /home/kuser/.config/systemd/user/pulseaudio.service
    # Everything under kuser needs to be owned by kuser.
    # IF not when doing the "systemctl --user enable pulseaudio.service" it will fail.
    chown -R kuser:kuser /home/kuser/.config

    touch /mnt/data/calls.log
    chmod ugo+w /mnt/data/calls.log

    loginctl enable-linger kuser

    systemctl daemon-reload

    if [ "$UPDATE" = true ]; then
        systemctl restart switch_mon.service
    else
        systemctl enable switch_mon.service
        systemctl start switch_mon.service
    fi

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


    # Start the service that monitors the Ext 200 VOIP line for calls.
    cp /mnt/data/voip_call_monitor.service /etc/systemd/system/.
    systemctl daemon-reload
    if [ "$UPDATE" = true ]; then
        systemctl restart voip_call_monitor.service
    else
        systemctl enable voip_call_monitor.service
        systemctl start voip_call_monitor.service
    fi


    # Start the service that monitors the connections to the 'elevator_conference' ARI
    # conference bridge.
    cp /mnt/data/voip_ari_conference.service /etc/systemd/system/.
    systemctl daemon-reload
    if [ "$UPDATE" = true ]; then
        systemctl restart voip_ari_conference.service
    else
        systemctl enable voip_ari_conference.service
        systemctl start voip_ari_conference.service
    fi


    cp /mnt/data/manage_modem.service /etc/systemd/system/.
    systemctl daemon-reload
    if [ "$UPDATE" = true ]; then
        systemctl restart manage_modem.service
    else
        systemctl enable manage_modem.service
        systemctl start manage_modem.service
    fi

    cp get_sensor_data.service get_sensor_data.timer /etc/systemd/system/
    systemctl daemon-reload
    if [ "$UPDATE" = true ]; then
        systemctl restart get_sensor_data.timer
    else
        systemctl enable get_sensor_data.timer
        systemctl start get_sensor_data.timer
    fi

    #systemctl status get_sensor_data.timer
    #systemctl list-timers get_sensor_data.timer

    cp /mnt/data/set-governor.service /etc/systemd/system/.
    systemctl daemon-reload
    if [ "$UPDATE" = true ]; then
        systemctl restart set-governor.service
    else
        systemctl enable set-governor.service
        systemctl start set-governor.service
    fi

    echo "Elevator configuration complete!"
fi

echo ""
echo "Kings3 installation finished successfully!"
