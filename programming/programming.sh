#!/bin/bash

echo "======================================"
echo "Kings III Q-Series Programming Utility"
echo "======================================"
echo ""

# Define the menu options
options=("First Telephone Number" "Second Telephone Number" "Third Telephone Number" "Zone Number(s)" "Customer Account Code" "Exit")
telephone_number_options=("Program Telephone Number" "Read Existing Telephone Number" "Exit to Main Menu")

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
                echo "Updating Zone Number(s)"
                # Replace with the actual command you want to run
                echo "done"
                ;;
            "Customer Account Code")
                echo "Updating Customer Account Code"
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
