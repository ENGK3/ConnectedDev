#!/bin/bash

echo "======================================"
echo "Kings III Q-Series Programming Utility"
echo "======================================"
echo ""

# Define the menu options
options=("First Telephone Number" "Second Telephone Number" "Third Telephone Number" "Zone Number(s)" "Customer Account Code" "Exit")
first_number_options=("Program First Telephone Number" "Read Existing First Telephone Number" "Exit to Main Menu")

first_number_submenu() {
    echo ""
    echo "======================================"
    echo "       First Phone Number Menu        "
    echo "======================================"
    echo ""

    select opt in "${first_number_options[@]}"
    do
        case $opt in
            "Program First Telephone Number")
                echo "Updating First Telephone Number"

                echo "done"
                ;;
            "Read Existing First Telephone Number")
                echo "First Telephone Number is ___"

                echo "done"
                ;;
            "Exit to Main Menu")
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
                # echo "Updating First Telephone Number"
                # Replace with the actual command you want to run
                # Example: gnome-terminal --command="bash -c 'ls -l; $SHELL'"
                # ls -l
                # echo "done"
                first_number_submenu
                ;;
            "Second Telephone Number")
                echo "Updating Second Telephone Number"
                # Replace with the actual command you want to run
                echo "done"
                ;;
            "Third Telephone Number")
                echo "Updating Third Telephone Number"
                # Replace with the actual command you want to run
                echo "done"
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
