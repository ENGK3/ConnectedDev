#!/bin/bash 

echo "Switch press detected" 

aplay -D plughw:1,0 /mnt/data/sounds/ENU00209.wav
