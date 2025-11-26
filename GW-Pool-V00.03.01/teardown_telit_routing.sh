#!/bin/bash

# Teardown PulseAudio loopbacks

echo "Tearing down audio routing..."

if [ -f /mnt/data/pulse/pulse_loopback_ids ]; then
    read TELIT_TO_SGTL SGTL_TO_TELIT < /mnt/data/pulse/pulse_loopback_ids

    pactl unload-module "$TELIT_TO_SGTL"
    pactl unload-module "$SGTL_TO_TELIT"

    echo "Unloaded modules:"
    echo "  TELIT → SGTL5000Card: Module ID $TELIT_TO_SGTL"
    echo "  SGTL5000Card → TELIT: Module ID $SGTL_TO_TELIT"

    rm /mnt/data/pulse/pulse_loopback_ids
else
    echo "No loopback module IDs found. Nothing to unload."
fi
