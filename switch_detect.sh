#!/bin/bash

echo "Switch press detected"

/mnt/data/led_green.sh OFF
/mnt/data/led_red.sh ON

# ENU00209.wav is the Emergency activation message
python3 /mnt/data/send_EDC_info.py -e "01"
aplay -D hw:SGTL5000Card,0 /mnt/data/sounds/ENU00209-48k.wav

# S0000303.wav is just the word "Delta" - useful for testing.
#aplay -D hw:SGTL5000Card,0 /mnt/data/sounds/S0000303.wav

# Remove the -n <number> to use the default EDC number
#python3 /mnt/data/place_call.py -v
python3 /mnt/data/place_call.py -n 9723256826 -v

/mnt/data/led_red.sh OFF
/mnt/data/led_green.sh ON

echo "Switch detection complete. Exiting to allow systemd restart."
