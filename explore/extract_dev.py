import re
import subprocess


def get_pactl_sources():
    try:
        # Run the pactl command and capture output
        result = subprocess.run(
            ["pactl", "list", "sources", "short"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print("Error running pactl:", result.stderr)
            return []

        interface_numbers = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 2:
                source_name = parts[1]
                match = re.search(
                    r"output.usb-Android_LE910C1-NF_[\w]+-(\d{2})\.", source_name
                )
                if match:
                    interface_numbers.append(match.group(1))
        return interface_numbers

    except Exception as e:
        print("Exception occurred:", e)
        return []


# Example usage
interfaces = get_pactl_sources()
print("LE910C1-NF Interface numbers:", interfaces[0])
