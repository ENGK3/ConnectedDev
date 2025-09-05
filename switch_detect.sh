#!/bin/bash

echo "Switch press detected"

/mnt/data/led_green.sh OFF
/mnt/data/led_red.sh ON

# ENU00209.wav is the Emergency activation message
aplay -D plughw:1,0 /mnt/data/sounds/ENU00209.wav

# S0000303.wav is just the word "Delta" - useful for testing.
#aplay -D plughw:1,0 /mnt/data/sounds/S0000303.wav

# Remove the -n <number> to use the default EDC number
# python3 /mnt/data/test_serial.py -v
python3 /mnt/data/test_serial.py -n 9723256826 -v

/mnt/data/led_red.sh OFF
/mnt/data/led_green.sh ON

echo "Switch detection complete. Exiting to allow systemd restart."
