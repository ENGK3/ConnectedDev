#!/bin/bash


if [[ "$1" == "ON" ]]; then
    echo "Turning RED LED ON"
    gpioset gpiochip1 28=1
elif [[ "$1" == "OFF" ]]; then
    echo "Turning RED LED OFF"
    gpioset gpiochip1 28=0
else
    echo "Unknown command: $1"
fi

