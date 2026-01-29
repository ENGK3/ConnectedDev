#!/bin/bash

echo "======================================"
echo "Kings III Q-Series Programming Utility"
echo "======================================"
echo ""

# Define the menu options
options=("First Telephone Number" "Second Telephone Number" "Third Telephone Number" "Zone Number(s)" "Customer Account Code" "Whitelist Settings" "Audio Settings" "System Info" "Exit")
telephone_number_options=("Program Telephone Number" "Read Existing Telephone Number" "Exit to Main Menu")
zone_list_options=("Program Zone Number(s)" "Read Existing Zone(s)" "Exit to Main Menu")
account_number_options=("Program Customer Account Number" "Read Existing Customer Account Number" "Exit to Main Menu")
whitelist_options=("Program Whitelist Number(s)" "Read Existing Whitelist Number(s)" "Exit to Main Menu")
audio_submenu_options=("Enable / Disable Speaker Audio" "Adjust Main Volume" "Adjust AVC Max Gain" "Adjust PCM Level" "Play Test Sound" "Exit to Main Menu")
sys_info_options=("Hardware Sensor Readings" "Cellular Info" "Exit to Main Menu")

first_number_submenu() {

    cfg_file="/mnt/data/K3_config_settings"
    key="FIRST_NUMBER"

    echo ""
    echo "======================================"
    echo "       First Phone Number Menu        "
    echo "======================================"
    echo ""

    select opt in "${telephone_number_options[@]}"
    do
        case $opt in
            "Program Telephone Number")
                echo ""
                echo "Please input new First Telephone Number:"
                read phone_number
                if [[ "$phone_number" =~ ^[+-]?[0-9]+$ ]]; then     # check to see if entry is only numbers
                    echo ""
                    echo "Updating First Telephone Number to \"$phone_number\""
                    if grep -q "^$key=" "$cfg_file"; then
                        # Key exists, update it
                        sed -i "s/^$key=.*/$key=\"$phone_number\"/" "$cfg_file"
                    else
                        # Key doesn't exist, append it
                        echo "$key=\"$phone_number\"" >> "$cfg_file"
                    fi
                    echo "done"
                else
                    echo ""
                    echo "Please enter only numerical values for telephone numbers!!!"
                fi
                ;;
            "Read Existing Telephone Number")
                VALUE=$(grep "^$key=" $cfg_file | cut -d '=' -f2)
                echo ""
                echo "First Telephone Number is $VALUE"
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "       First Phone Number Menu        "
        echo "======================================"
        echo ""
    done
}

second_number_submenu() {

    cfg_file="/mnt/data/K3_config_settings"
    key="SECOND_NUMBER"

    echo ""
    echo "======================================"
    echo "       Second Phone Number Menu       "
    echo "======================================"
    echo ""

    select opt in "${telephone_number_options[@]}"
    do
        case $opt in
            "Program Telephone Number")
                echo ""
                echo "Please input new Second Telephone Number:"
                read phone_number
                if [[ "$phone_number" =~ ^[+-]?[0-9]+$ ]]; then     # check to see if entry is only numbers
                    echo ""
                    echo "Updating Second Telephone Number to \"$phone_number\""
                    if grep -q "^$key=" "$cfg_file"; then
                        # Key exists, update it
                        sed -i "s/^$key=.*/$key=\"$phone_number\"/" "$cfg_file"
                    else
                        # Key doesn't exist, append it
                        echo "$key=\"$phone_number\"" >> "$cfg_file"
                    fi
                    echo "done"
                else
                    echo ""
                    echo "Please enter only numerical values for telephone numbers!!!"
                fi
                ;;
            "Read Existing Telephone Number")
                VALUE=$(grep "^$key=" $cfg_file | cut -d '=' -f2)
                echo ""
                echo "Second Telephone Number is $VALUE"
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "       Second Phone Number Menu       "
        echo "======================================"
        echo ""
    done
}

third_number_submenu() {

    cfg_file="/mnt/data/K3_config_settings"
    key="THIRD_NUMBER"

    echo ""
    echo "======================================"
    echo "       Third Phone Number Menu        "
    echo "======================================"
    echo ""

    select opt in "${telephone_number_options[@]}"
    do
        case $opt in
            "Program Telephone Number")
                echo ""
                echo "Please input new Third Telephone Number:"
                read phone_number
                if [[ "$phone_number" =~ ^[+-]?[0-9]+$ ]]; then     # check to see if entry is only numbers
                    echo ""
                    echo "Updating Third Telephone Number to \"$phone_number\""
                    if grep -q "^$key=" "$cfg_file"; then
                        # Key exists, update it
                        sed -i "s/^$key=.*/$key=\"$phone_number\"/" "$cfg_file"
                    else
                        # Key doesn't exist, append it
                        echo "$key=\"$phone_number\"" >> "$cfg_file"
                    fi
                    echo "done"
                else
                    echo ""
                    echo "Please enter only numerical values for telephone numbers!!!"
                fi
                ;;
            "Read Existing Telephone Number")
                VALUE=$(grep "^$key=" $cfg_file | cut -d '=' -f2)
                echo ""
                echo "Third Telephone Number is $VALUE"
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "       Third Phone Number Menu        "
        echo "======================================"
        echo ""
    done
}

zone_number_submenu() {

    cfg_file="/mnt/data/K3_config_settings"
    key="ZLST"

    echo ""
    echo "======================================"
    echo "          Zone Number(s) Menu         "
    echo "======================================"
    echo ""

    select opt in "${zone_list_options[@]}"
    do
        case $opt in
            "Program Zone Number(s)")
                echo ""
                echo "Please input new Zone Number(s), in the format \"01020304\" for four Zones, for example:"
                read zone_info
                if [[ "$zone_info" =~ ^[+-]?[0-9]+$ ]]; then     # check to see if entry is only numbers
                    echo ""
                    echo "Updating Zone(s) to \"$zone_info\""
                    if grep -q "^$key=" "$cfg_file"; then
                        # Key exists, update it
                        sed -i "s/^$key=.*/$key=\"$zone_info\"/" "$cfg_file"
                    else
                        # Key doesn't exist, append it
                        echo "$key=\"$zone_info\"" >> "$cfg_file"
                    fi
                    echo "done"
                else
                    echo ""
                    echo "Please enter only numerical values for Zone numbers!!!"
                fi
                ;;
            "Read Existing Zone(s)")
                VALUE=$(grep "^$key=" $cfg_file | cut -d '=' -f2)
                echo ""
                echo "Listed Zone(s): $VALUE"
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "          Zone Number(s) Menu         "
        echo "======================================"
        echo ""
    done
}

account_number_submenu() {

    cfg_file="/mnt/data/K3_config_settings"
    key="AC"

    echo ""
    echo "======================================"
    echo "     Customer Account Number Menu     "
    echo "======================================"
    echo ""

    select opt in "${account_number_options[@]}"
    do
        case $opt in
            "Program Customer Account Number")
                echo ""
                echo "Please input new Customer Account Number:"
                read account_number

                echo ""
                echo "Updating Customer Account Number to \"$account_number\""
                if grep -q "^$key=" "$cfg_file"; then
                    # Key exists, update it
                    sed -i "s/^$key=.*/$key=\"$account_number\"/" "$cfg_file"
                else
                    # Key doesn't exist, append it
                    echo "$key=\"$account_number\"" >> "$cfg_file"
                fi
                echo "done"

                ;;
            "Read Existing Customer Account Number")
                VALUE=$(grep "^$key=" $cfg_file | cut -d '=' -f2)
                echo ""
                echo "Listed Customer Account Number: $VALUE"
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "     Customer Account Number Menu     "
        echo "======================================"
        echo ""
    done
}

whitelist_submenu() {
    cfg_file="/mnt/data/K3_config_settings"
    key="WHITELIST"

    echo ""
    echo "======================================"
    echo "       Whitelist Settings Menu        "
    echo "======================================"
    echo ""

    select opt in "${whitelist_options[@]}"
    do
        case $opt in
            "Program Whitelist Number(s)")
                append=0
                write=1

                echo ""
                echo "Enter '0' to append number to whitelist, or enter '1' to erase and write a new number to the whitelist:"
                read write_option
                if [[ "$write_option" -eq "$append" ]]; then
                    current_whitelist=$(grep "^${key}=" "$cfg_file" | sed -e "s/^${key}=//" -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                    echo "Please input new number to append to whitelist:"
                    read phone_number_append
                    if [[ "$phone_number_append" =~ ^[+-]?[0-9]+$ ]]; then     # check to see if entry is only numbers
                        echo ""
                        echo "Appending new number ($phone_number_append) to whitelist"
                        if grep -q "^$key=" "$cfg_file"; then
                            # Key exists, update it
                            sed -i "s/^$key=.*/$key=\"$current_whitelist,$phone_number_append\"/" "$cfg_file"
                        fi
                        echo "done"
                    else
                        echo ""
                        echo "Please enter only numerical values for telephone numbers!!!"
                    fi
                fi
                if [[ "$write_option" -eq "$write" ]]; then
                    echo "Erasing whitelist... Please input new number to write to whitelist:"
                    read phone_number_write
                    if [[ "$phone_number_write" =~ ^[+-]?[0-9]+$ ]]; then     # check to see if entry is only numbers
                        echo ""
                        echo "Writing new number ($phone_number_write) to whitelist"
                        if grep -q "^$key=" "$cfg_file"; then
                            # Key exists, update it
                            sed -i "s/^$key=.*/$key=\"$phone_number_write\"/" "$cfg_file"
                        else
                            # Key doesn't exist, append it
                            echo "$key=\"$phone_number_write\"" >> "$cfg_file"
                        fi
                        echo "done"
                    else
                        echo ""
                        echo "Please enter only numerical values for telephone numbers!!!"
                    fi
                fi
                ;;
            "Read Existing Whitelist Number(s)")
                VALUE=$(grep "^$key=" $cfg_file | cut -d '=' -f2)
                echo ""
                echo "Listed Whitelist Number(s): $VALUE"
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "       Whitelist Settings Menu        "
        echo "======================================"
        echo ""
    done
}

audio_submenu() {

    echo ""
    echo "======================================"
    echo "         Audio Settings Menu          "
    echo "======================================"
    echo ""

    select opt in "${audio_submenu_options[@]}"
    do
        case $opt in
            "Enable / Disable Speaker Audio")
                on=1
                off=0
                echo ""
                echo "Enter 0 to disable audio, or 1 to enable audio"
                read response
                    if [[ "$response" -eq "$off" ]]; then
                        amixer set Lineout off
                        echo ""
                        echo "Audio disabled"
                    fi
                    if [[ "$response" -eq "$on" ]]; then
                        amixer set Lineout on
                        echo ""
                        echo "Audio enabled"
                    fi
                ;;
            "Adjust Main Volume")
                echo ""
                amixer get Lineout
                echo ""
                echo "Enter the desired Main Volume setting from 0-100"
                read main_vol
                amixer set Lineout $main_vol%
                ;;
            "Adjust AVC Max Gain")
                echo ""
                amixer get 'AVC Max Gain'
                echo ""
                echo "Enter the desired Gain setting from 0-2"
                read gain
                amixer set 'AVC Max Gain' $gain
                ;;
            "Adjust PCM Level")
                echo ""
                amixer get 'PCM'
                echo ""
                echo "Enter the desired PCM Volume setting from 0-100"
                read pcm_level
                amixer set 'PCM' $pcm_level%
                ;;
            "Play Test Sound")
                echo ""
                aplay /usr/share/sounds/alsa/Front_Center.wav
                echo ""
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "         Audio Settings Menu          "
        echo "======================================"
        echo ""
    done
}

sys_info_submenu() {

    cfg_file="/mnt/data/K3_config_settings"
    key="CID"

    echo ""
    echo "======================================"
    echo "           System Info Menu           "
    echo "======================================"
    echo ""

    select opt in "${sys_info_options[@]}"
    do
        case $opt in
            "Hardware Sensor Readings")
                eval $(python3 /mnt/data/programming/menu_sensor_update.py)
                echo ""
                echo "System Voltage: $sys_voltage V"
                echo "System Temperature: $sys_temperature *C"
                ;;
            "Cellular Info")
                eval $(python3 /mnt/data/programming/menu_modem_stats.py)
                # cid=$(grep "^$key=" $cfg_file | cut -d '=' -f2)
                cid=$(grep "^${key}=" "$cfg_file" | sed -e "s/^${key}=//" -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                echo ""
                echo "Caller ID Number: $cid"
                echo "ICCID: $iccid"
                echo "IMEI: $imei"
                echo "IMSI: $imsi"
                echo "RSRQ: $rsrq dBm"
                echo "RSRP: $rsrp dBm"
                echo "Modem Temp: $modem_temp *C"
                echo "Network: $network"
                echo "IMS Registration: $ims_reg"
                echo "Signal Quality: $signal_quality dBm"
                echo "Facility Lock: $facility_lock"
                echo "APN: $apn"
                ;;
            "Exit to Main Menu")
                echo ""
                echo "Exiting to main menu..."
                return
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "           System Info Menu           "
        echo "======================================"
        echo ""
    done
}

while true; do
    # Start the select loop to display the menu
    echo ""
    echo "======================================"
    echo "              Main Menu               "
    echo "======================================"
    echo ""
    select opt in "${options[@]}"
    do
        case $opt in
            "First Telephone Number")
                first_number_submenu
                ;;
            "Second Telephone Number")
                second_number_submenu
                ;;
            "Third Telephone Number")
                third_number_submenu
                ;;
            "Zone Number(s)")
                zone_number_submenu
                ;;
            "Customer Account Code")
                account_number_submenu
                ;;
            "Whitelist Settings")
                whitelist_submenu
                ;;
            "Audio Settings")
                audio_submenu
                ;;
            "System Info")
                sys_info_submenu
                ;;
            "Exit")
                echo ""
                echo "Exiting..."
                echo ""
                exit
                ;;
            *)
                echo "Invalid option $REPLY"
                ;;
        esac
        REPLY=  # This line forces the menu to redraw on the next loop
        echo ""
        echo "======================================"
        echo "              Main Menu               "
        echo "======================================"
        echo ""
    done
done
