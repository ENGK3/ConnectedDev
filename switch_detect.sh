#!/bin/bash 

echo "Switch press detected" 

echo "Switch press detected"

./led_green.sh OFF
./led_red.sh ON


aplay -D plughw:1,0 /mnt/data/sounds/ENU00209.wav
#aplay -D plughw:1,0 /mnt/data/sounds/S0000303.wav
sleep 1
python3 test_serial.py -n 9723256826 -v True

./led_red.sh OFF
./led_green.sh ON

