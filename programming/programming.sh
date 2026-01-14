#!/bin/bash

echo "======================================"
echo "Kings III Q-Series Programming Utility"
echo "======================================"
echo ""

# Define the menu options
options=("First Telephone Number" "Second Telephone Number" "Third Telephone Number" "Zone Number(s)" "Customer Account Code" "System Info" "Exit")
telephone_number_options=("Program Telephone Number" "Read Existing Telephone Number" "Exit to Main Menu")
zone_list_options=("Program Zone Number(s)" "Read Existing Zone(s)" "Exit to Main Menu")

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
    echo "           Zone Config Menu           "
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
                    echo "Please enter only numerical values for telephone numbers!!!"
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
        echo "           Zone Config Menu           "
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
                echo "Updating Customer Account Code"
                # Replace with the actual command you want to run
                echo "done"
                ;;
            "System Info")
                echo ""
                echo "Fetching System Info"
                # Replace with the actual command you want to run
                echo "done"
                ;;
            "Exit")
                echo "Exiting..."
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
