#!/bin/bash

script_to_run=/mnt/data/switch_detect.sh

echo "Script to run is $script_to_run"
echo ""

if [ ! -e /tmp/setup ]; then
	/mnt/data/led_red.sh ON
	/mnt/data/led_green.sh ON
	/mnt/data/led_blue.sh OFF

	# Check the result of check_reg.py
	python3 /mnt/data/check_reg.py -q
	if [ $? -ne 0 ]; then
		/mnt/data/led_green OFF
		/mnt/data/led_red.sh OFF
		/mnt/data/led_blue.sh ON
		exit 0
	fi
fi

/mnt/data/led_red.sh OFF
/mnt/data/led_green.sh ON

gpiomon --falling-edge --num-events=1 gpiochip1 24 | while read -r line; do
	echo $0
	$script_to_run
done


