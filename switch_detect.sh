#!/bin/bash 

echo "Switch press detected" 

/mnt/data/led_green.sh OFF
/mnt/data/led_red.sh ON


#aplay -D plughw:1,0 /mnt/data/sounds/ENU00209.wav
aplay -D plughw:1,0 /mnt/data/sounds/S0000303.wav
sleep 1
python3 /mnt/data/test_serial.py -n 9723256826 -v True

/mnt/data/led_red.sh OFF
/mnt/data/led_green.sh ON

