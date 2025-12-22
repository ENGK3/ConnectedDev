#!/bin/bash

# Set proper working directory
cd /mnt/data

script_to_run=/mnt/data/switch_detect.sh

GPIO_CHIP=0
GPIO_PIN=7


echo "Script to run is $script_to_run"
echo ""

# Function to cleanup GPIO resources
cleanup_gpio() {
    echo "Cleaning up GPIO resources..."
    # Kill any existing gpiomon processes
    pkill -f "gpiomon.*gpiochip$GPIO_CHIP.*$GPIO_PIN" 2>/dev/null || true
    sleep 1
}

# Trap signals for proper cleanup
trap cleanup_gpio EXIT INT TERM

if [ ! -e /tmp/setup ]; then
    /mnt/data/led_red.sh ON
	/mnt/data/led_green.sh OFF
#	/mnt/data/led_blue.sh OFF

	# Check the result of check_reg.py
	python3 /mnt/data/check_reg.py -q -r
	if [ $? -ne 0 ]; then
		/mnt/data/led_green.sh OFF
        /mnt/data/led_red.sh OFF
#		/mnt/data/led_blue.sh ON
		exit 0
	fi
fi

/mnt/data/led_red.sh OFF
/mnt/data/led_green.sh ON
#/mnt/data/led_blue.sh OFF

# Cleanup any existing GPIO monitors before starting
cleanup_gpio

# Use a more robust approach for GPIO monitoring
while true; do
    echo "Starting GPIO monitor..."

    # Use timeout to prevent hanging
    gpiomon --bias=pull-up --falling-edge --num-events=1 gpiochip$GPIO_CHIP $GPIO_PIN
    gpio_exit_code=$?

    if [ $gpio_exit_code -eq 0 ]; then
        echo "GPIO event detected, running switch detection script..."
        $script_to_run
        # Don't restart automatically here - let systemd handle restarts
        break
    # elif [ $gpio_exit_code -eq 124 ]; then
    #     echo "GPIO monitor timed out after 1 hour, restarting..."
    #     cleanup_gpio
    #     continue
    else
        echo "GPIO monitor failed with exit code $gpio_exit_code"
        sleep 5
        cleanup_gpio
        continue
    fi
done
