import json
import subprocess


def update_sensor_data():
    try:
        # Run the command and capture output
        result = subprocess.run(
            ["sensors", "-j"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Error fetching sensor data:", result.stderr)
            return False

        output = json.loads(result.stdout)
        return output

    except Exception as e:
        print("Exception occurred:", e)
        return []


# update sensors and load into .json file
data = update_sensor_data()

voltage = data["gsc_hwmon-isa-0000"]["vdd_vin"]["in1_input"]
temp = data["cpu_thermal-virtual-0"]["temp1"]["temp1_input"]

print(f"export sys_voltage='{voltage}'")
print(f"export sys_temperature='{temp}'")
