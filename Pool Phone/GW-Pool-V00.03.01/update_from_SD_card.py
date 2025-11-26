import os
import subprocess
from dotenv import dotenv_values, set_key
from pathlib import Path

home_dir = "/mnt/data"
mount_dir = "/mnt/sd_card"
sd_dir = "/dev/mmcblk1p1"
hw_app = "Pool"

def check_for_sd_card():
    try:
        # Run the command and capture output
        result = subprocess.run(
            ["mount", sd_dir, mount_dir],
            capture_output=True,
            text=True,
        )
        # print('Return code: ' + str(result.returncode))
        if result.returncode != 0:
            if result.returncode == 32:
                print("Drive already mounted!")
                return True
            else:
                print("Error mounting drive:", result.stderr)
                return False
        if result.returncode == 0:
            print("Drive mounted!")
            return True

    except Exception as e:
        print("Exception occurred:", e)
        return []

def check_mounting_path():
    if not os.path.exists(mount_dir):
        try:
            # Run the command and capture output
            result = subprocess.run(
                ["mkdir", mount_dir],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print("Error creating path:", result.stderr)
                return False
            if result.returncode == 0:
                print("Path created!")
                return True
        except Exception as e:
            print("Exception occurred:", e)
            return []
    if os.path.exists(mount_dir):
        print("Path exists!")
        return True

def copy_file(SRC_PATH, DEST_PATH):
    try:
        # Run the command and capture output
        result = subprocess.run(
            ["cp", SRC_PATH, DEST_PATH],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("Error copying file(s):", result.stderr)
            return False
        if result.returncode == 0:
            print("File(s) copied!")
            return True

    except Exception as e:
        print("Exception occurred:", e)
        return []
    
def extract_tar(FILE_NAME, DEST_PATH):
    try:
        # Run the command and capture output
        result = subprocess.run(
            ["tar", "-zxf", FILE_NAME, "-C", DEST_PATH],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("Error extracting tar archive:", result.stderr)
            return False
        if result.returncode == 0:
            print("Archive extracted!")
            return True

    except Exception as e:
        print("Exception occurred:", e)
        return []

def get_current_sw_version():
    try:
        # Run the command and capture output
        result = subprocess.run(
            ["source", "/mnt/data/K3_config_settings"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("Error setting source:", result.stderr)
            return False
        
        result = subprocess.run(
            ["echo", "$SW_VERSION"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("Error setting source:", result.stderr)
            return False
        
    except Exception as e:
        print("Exception occurred:", e)
        return []

print('')

# check if a mounting directory exists, create if necessary
if check_mounting_path():
    # determine if an SD card is present
    if check_for_sd_card():
        print('')
        
        if os.path.exists('/mnt/data/K3_config_settings'):
            # get version of currently installed SW
            config = dotenv_values("/mnt/data/K3_config_settings")
            uut_sw_version = config.get("SW_VERSION","MISSING_SW_VERSION")
            uut_hw_app = config.get("HW_APP","MISSING_HW_APP")

            # get version of update package
            update_dir = Path(mount_dir)
            tgz_file_list = list(update_dir.rglob("*.tgz"))
            update_file = str(tgz_file_list[0])
            update_sw_version = update_file[-12:-4]
            tar_name = update_file.split('/')[3]

            # compare versions
            uut_compare = int(uut_sw_version.replace('.',''))
            sw_compare = int(update_sw_version.replace('.',''))

            file_delta = uut_compare - sw_compare

            if (file_delta > 0) and (uut_hw_app == hw_app):
                print('Installed ' + uut_hw_app + ' software is a newer version (V' + uut_sw_version + ') - aporting update')
            if (file_delta == 0) and (uut_hw_app == hw_app):
                print(uut_hw_app + ' software is already at the latest version (V' + uut_sw_version + ')')
            if (file_delta < 0) and (uut_hw_app == hw_app):
                # make a copy of config file in other directory
                if copy_file('/mnt/data/K3_config_settings', '/mnt'):
                    # update older files & copy over anything new that's missing
                    if copy_file(update_file, home_dir):
                        if extract_tar(home_dir + '/' + tar_name, home_dir):
                            # copy over previous config file
                            if copy_file('/mnt/K3_config_settings', '/mnt/data'):
                                # update SW version in config file
                                set_key("/mnt/data/K3_config_settings", "SW_VERSION", update_sw_version)
                                print('')
                                print('File update complete!')

print('done')