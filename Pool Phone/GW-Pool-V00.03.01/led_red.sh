#!/bin/bash

# Red LED is on GPIO 18 on gpiochip4 on the Gateworks board GW7200.
CHIP=4
GPIO=26

if [[ "$1" == "ON" ]]; then
    echo "Turning RED LED ON"
    gpioset gpiochip$CHIP $GPIO=1
elif [[ "$1" == "OFF" ]]; then
    echo "Turning RED LED OFF"
    gpioset gpiochip$CHIP $GPIO=0
else
    echo "Unknown command: $1"
fi

