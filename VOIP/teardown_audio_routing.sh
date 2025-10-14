#!/bin/bash

# Teardown PulseAudio loopbacks

echo "Tearing down audio routing..."

if [ -f /mnt/data/pulse/pulse_loopback_ids ]; then
    read HEADSET_TO_SGTL SGTL_TO_HEADSET < /mnt/data/pulse/pulse_loopback_ids

    pactl unload-module "$HEADSET_TO_SGTL"
    pactl unload-module "$SGTL_TO_HEADSET"

    echo "Unloaded modules:"
    echo "  Headset → SGTL5000Card: Module ID $HEADSET_TO_SGTL"
    echo "  SGTL5000Card → Headset: Module ID $SGTL_TO_HEADSET"

    rm /mnt/data/pulse/pulse_loopback_ids
else
    echo "No loopback module IDs found. Nothing to unload."
fi
