# Digiboard CC6 Programming


The program UUU is needed (using a Linux VM is the easiest). Connect the USB OTG port, on the bottom of the board under the full
sized USB ports to your PC. ( Linux is the easiest). A FTDI USB-RS232 cable is needed to connect the serial port.
Connect a serial console port (FDTI cable which is TRUE RS232 (negative voltage)) is needed to connect to Digi board (Ref Des. XX).
Having an Ethernet port connected also facilitates getting the Pool application files onto the board more easily.

Set BOOT Config switches to (both switches) to ON.

Getting the image:
** TODO ** Add instructions and links to where to get the image.
The package needed is for the ccimx6sbc  module and ccimx6sbc-installer.zip should be retrieved and unzipped.
https://ftp1.digi.com/support/digiembeddedyocto/4.0/r7/images/ccimx6sbc/


In the Linux VM,

```
sudo uuu u-boot-ccimx6qsbc.imx
```
This will allow the serial USB connection to be recognized as soon as the SBC is powered up.

Power up SBC.
This is what the screen should look like once the programming is complete.
```
alanh@alanh-VMware-Virtual-Platform:~/K3$ sudo uuu u-boot-ccimx6qsbc.imx
[sudo] password for alanh:
uuu (Universal Update Utility) for nxp imx chips -- libuuu_1.5.219-0-gb776f70

Success 1    Failure 0


2:1-         2/ 2 [Done                                  ] SDP: done
```
This will boot the SBD into a UBoot instance in Ram.
The next step is program the UBoot image in ram needs to get to be written to emmc.
```
=> update uboot ram
Do you really want to program the boot loader? <y/N> y
switch to partitions #1, OK
mmc0(part 1) is current device

MMC write: dev # 0, block # 2, count 0 ... 0 blocks written: OK
Reading back firmware...

MMC read: dev # 0, block # 2, count 0 ... 0 blocks read: OK
Verifying firmware...
Total of 0 word(s) were the same
Update was successful
switch to partitions #0, OK
mmc0(part 0) is current device
```

Once this is done power off the board, and reset the Boot config switches to OFF (towards the center of the board).
Power the board on and it will stop in the uboot process because there is no Kernel or Root File System (RFS) loaded.
This will partition the emmc0.
```
setenv mmcdev 0

run partition_mmc_linux

fastboot 0
```
Leave the USB OTG connected. This "fastboot 0" will cause the USB OTG port to become active again.
Run the following on the Linux machine where the USB OTG is connected.
```
sudo ./install_linux_fw_uuu.sh
```

This will program in the Kernel and the RFS and some other partitions. The operation will produce output on the serial console show it is making progress,
as well as on the terminal where the command was run.

The SBC will reboot at least once after the programming and it will take almost a minute to reach a prompt.

In order for the USB Audio channel to be seen from the LE910 modem, the USBCFG register must be changed.

```
microcom -s 115200 /dev/ttyUSB2
ATE1
OK
AT#USBCFG=11

```
This will cause the LTE modem to reconfigure itself and reboot. There will be several messages on the console when this happens.
Once this process has completed, the following should be seen
```
root@ccimx6sbc:~# lsusb
Bus 001 Device 004: ID 1bc7:1230 Telit Wireless Solutions LE910C1-NF
Bus 001 Device 002: ID 0424:2514 Microchip Technology, Inc. (formerly SMSC) USB 2.0 Hub
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
```

At this point there should be a network information on the SBC. On the SBC console,
```
root@ccimx6sbc:~# ifconfig eth0
eth0      Link encap:Ethernet  HWaddr 00:04:F3:3D:A6:3E
          inet addr:172.20.10.137  Bcast:172.20.10.255  Mask:255.255.255.0
          inet6 addr: fe80::204:f3ff:fe3d:a63e/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:220 errors:0 dropped:0 overruns:0 frame:0
          TX packets:88 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:23653 (23.0 KiB)  TX bytes:9729 (9.5 KiB)
```

Clone the git repo git@github.com:ConnectedDevelopment/K3-Qseries-POC.git.

Next up is to copy the Pool application code to the /mnt/data directory.

The easiest way to do this is to modify the "justfile" from the cloned repo to have the IP address of the SBC found in the
eth0 interface in the ifconfig output. In this case it was "172.20.10.137". Note this does require the tool "just" to be installed.
This can also be done from the Linux VM if it can access the target device.
```
target := "172.20.10.137"
```

```
just push
```

After this completes, the following commands need to be executed to get the system configured.

```
cp /mnt/data/99-ignore-modemmanager.rules  /etc/udev/rules.d/99-ignore-modemmanager.rules
cp /mnt/data/switch_mon.service /etc/systemd/system/switch_mon.service

systemctl stop weston.service
systemctl disable weston.service
systemctl stop connectcore-demo-server.service
systemctl disable connectcore-demo-server.service

systemctl daemon-reload
systemctl enable switch_mon.service
```

At this point it is necessary to copy the correct Kernel and modules to the board.
Open a Powershell window at the following directory.
```
....\Exponential Technology Group, Inc\C_KingsIII-QSeries - Documents\sw
```
The "...." in front of the path is going to be dependent on where the "C_KingsIII-QSeries - Documents"
directory is mapped on the machine where the copy will be performed.
The files to be copied to the device target are "zImage" and "digi-modules-5_15_71.tar.gz"
Before these files are copied across to the target, the following steps should be executed.
On the SBC console. The linux partition is mounted read-only so it needs to be remounted as r/w to
be able to update the Kernel.

```
umount /mnt/linux
mount /dev/mmcblk0p1 /mnt/linux

mv /mnt/linux/zImage-ccimx6sbc.bin /mnt/linux/zImage-ccimx6sbc.bin.orig
mv /lib/modules/5.15.71-dey-dey /lib/modules/old-5.15.71-dey-dey
```

Note this is the target IP address used earlier.  You might see the following dialog if this is the
first time to connect to this target from Powershell.

```
❯ scp .\zImage root@172.20.10.137:/mnt/linux/zImage-ccimx6sbc.bin
The authenticity of host '172.20.10.137 (172.20.10.137)' can't be established.
RSA key fingerprint is SHA256:Kc9nZWupHy2axrHPw5fyiD4MfJ1QDEaR6A/ijgeBTz0.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
Warning: Permanently added '172.20.10.137' (RSA) to the list of known hosts.
zImage                                        100% 7470KB   3.9MB/s   00:01

scp digi-modules-5_15_71.tar.gz root@172.20.10.137:/lib/modules
digi-modules-5_15_71.tar.gz                   100% 1604KB   2.9MB/s   00:00
```

Then back on the SBC console, unzip the modules that match the Kernel.
```
cd /lib/modules
tar -xzv --strip-components=3 -f digi-modules-5_15_71.tar.gz
rm -rf digi-modules-5_15_71.tar.gz
```

Once this is complete make sure there is a Kernel and a matching modules i.e.
```
root@ccimx6sbc:/lib/modules# ls -l /mnt/linux/zImage-ccimx6sbc.bin /lib/modules
-rwxr-xr-x    1 root     root       7648920 Sep  8 19:05 /mnt/linux/zImage-ccimx6sbc.bin

/lib/modules:
drwxrwxr-x    3 weston   weston        4096 Sep  8 19:23 5.15.71+
drwxr-xr-x    4 root     root          4096 Oct  8  2024 old-5.15.71-dey-dey
```

Now shutdown the unit, unplug the power, count to ten and plug it back in to the power again.
```
shutdown -h now
..... lots of output.
....
systemd-shutdown[1]: All filesystems, swaps, loop devices, MD devices and DM devices detached.
systemd-shutdown[1]: Syncing filesystems and block devices.
systemd-shutdown[1]: Powering off.
sgtl5000 2-000a: ASoC: error at snd_soc_component_update_bits on sgtl5000.2-000a: -11
sgtl5000 2-000a: ASoC: error at snd_soc_component_update_bits on sgtl5000.2-000a: -11
ci_hdrc ci_hdrc.1: remove, state 1
usb usb1: USB disconnect, device number 1
usb 1-1: USB disconnect, device number 2
usb 1-1.3: USB disconnect, device number 3
option1 ttyUSB0: GSM modem (1-port) converter now disconnected from ttyUSB0
option 1-1.3:1.0: device disconnected
qmi_wwan 1-1.3:1.2 wwan0: unregister 'qmi_wwan' usb-ci_hdrc.1-1.3, WWAN/QMI device
option1 ttyUSB1: GSM modem (1-port) converter now disconnected from ttyUSB1
option 1-1.3:1.6: device disconnected
option1 ttyUSB2: GSM modem (1-port) converter now disconnected from ttyUSB2
option 1-1.3:1.7: device disconnected
option1 ttyUSB3: GSM modem (1-port) converter now disconnected from ttyUSB3
option 1-1.3:1.8: device disconnected
option1 ttyUSB4: GSM modem (1-port) converter now disconnected from ttyUSB4
option 1-1.3:1.9: device disconnected
ci_hdrc ci_hdrc.1: USB bus 1 deregistered
reboot: Power down
```

Unplug the USB OTG cable that was connected to the Linux VM.
If this is not done, the system console will not return on the reboot because it is being re-routed over the USB.

Plug in the device again.
Once the machine has been booted again, the ALSA mixer needs to be "adjusted".
The items to check for in the ALSA mixer tool are as follows.

```
alsactl --file /mnt/data/asound.state restore
alsactl store
```
Note - there might be the following output from the restore command.
```
alsa-lib ../../../alsa-lib-1.2.6.1/src/ucm/main.c:1412:(snd_use_case_mgr_open) error: failed to import hw:0 use case configuration -2
alsa-lib ../../../alsa-lib-1.2.6.1/src/ucm/main.c:1412:(snd_use_case_mgr_open) error: failed to import hw:1 use case configuration -2
```


The settings can be tested with the following command
```
aplay -D plughw:1,0 /mnt/data/sounds/S0000304.wav
```
The tool alsamixer can be used to tweak the sound card settings as necessary.
BUT be sure to do a
```
alsactl store
```
afterwards to make sure you have the settings saved.


**NOTE** The script /mnt/data/switch_dected.sh can be edited to specify a number to dial.
Currently the number dialed is that of the EDC (9723507770) which is the default number of the
place_call.py script.
The following line can be changed to change the number dialed.
```
python3 /mnt/data/place_call.py -v
#should be change like the line below to dial a NON EDC number.
python3 /mnt/data/place_call.py -n 1112223333 -v
```
