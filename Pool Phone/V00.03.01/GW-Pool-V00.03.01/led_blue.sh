#!/bin/bash


if [[ "$1" == "ON" ]]; then
    echo "Turning GREEN LED ON"
    gpioset gpiochip1 7=1
elif [[ "$1" == "OFF" ]]; then
    echo "Turning GREEN LED OFF"
    gpioset gpiochip1 7=0
else
    echo "Unknown command: $1"
fi

