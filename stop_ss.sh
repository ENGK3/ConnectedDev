#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Must be root to execute"
    exit 1
fi

systemctl stop get_sensor_data.service \
voip_call_monitor.service \
voip_ari_conference.service \
manage_modem.service \
