#!/bin/bash


script_to_run=/mnt/data/switch_detect.sh

echo "Script to run is $script_to_run"
echo "" 

gpiomon --falling-edge --num-events=1 gpiochip1 24 | while read -r line; do 
echo $0
$script_to_run

done


