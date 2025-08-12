#!/bin/bash


done

script_to_run=/mnt/data/switch_detect.sh

echo "Script to run is $script_to_run"
echo "" 

# /mnt/data/led_red.sh ON
# /mnt/data/led_green.sh ON

# # Check the result of check_reg.py
# result=$(python3 /mnt/data/check_reg.py)
# if [ "$result" -eq 0 ]; then
# 	python3 /mnt/data/led_blue.py ON
# 	exit 0
# fi

/mnt/data/led_red.sh OFF
/mnt/data/led_green.sh ON

gpiomon --falling-edge --num-events=1 gpiochip1 24 | while read -r line; do 
	echo $0
	$script_to_run
done


