#!/bin/bash

# Green LED is on GPIO 9 on gpiochip0 on the Gateworks board GW7200.
CHIP=0
GPIO=9


if [[ "$1" == "ON" ]]; then
    echo "Turning GREEN LED ON"
    gpioset gpiochip$CHIP $GPIO=1
elif [[ "$1" == "OFF" ]]; then
    echo "Turning GREEN LED OFF"
    gpioset gpiochip$CHIP $GPIO=0
else
    echo "Unknown command: $1"
fi

