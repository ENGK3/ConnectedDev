# Gateworks Venice Programming for VOIP solution

The Gateworks setup for the VOIP solution is different than that for the Pool
configuration. In the VOIP configuration the ethernet port eth0 is used to get Power
Over Ethernet(POE), and to connect to the POE switch. The second interface will be
needed to connect to the internet for installing update and packages.

## Setup

To be able to get to the system console on first powering up of the board, the JTAG
debugger will be needed.
It will allow the system console to be presented to the PC as a serial port.

## Connectivity

Connect the USB/Serial/JTAG debugger cable for the system console and let the board
boot normally the first time.
Login with root.

If the ethernet interface doesn't come up and get an ip address.

```bash
root@noble-venice:~# ip addr show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 00:d0:12:07:fa:02 brd ff:ff:ff:ff:ff:ff
    altname end0
    inet 172.20.10.71/24 brd 172.20.10.255 scope global dynamic noprefixroute eth0
       valid_lft 601249sec preferred_lft 525744sec
    inet6 fe80::d6dd:4eca:da70:827d/64 scope link
       valid_lft forever preferred_lft forever
```

The issue the following command

```bash
dhcpcd eth0
```

Similarly for eth1.
Make sure that eth1 has internet access.

Before running updates for the packages, make sure that the eth0 is disabled, or
the command below will fail because it will be going to a network interface that does
not have internet access.

## Push VOIP phone scripts

To be able to push the voip setup scripts to the Gateworks board a user needs to be
created

```bash
adduser kuser
```

And create the user with a password. REMEMBER the password.

This user on the target needs to have some additional permissions granted.
These are for accessing the modem and gpios and provides some additional security since
the application is not being run as root.

```bash
usermod -aG dialout,audio,plugdev  kuser
```



## Packages

```bash
apt-get install baresip asterisk python3-serial microcom pulseaudio
```

## Setup and Configuration

The following edits are appended to the '/etc/pulse/default.pa' file.

### PulseAudio

```bash
set-card-profile alsa_card.usb-Android_LE910C1-NF_0123456789ABCDEF-04 output:mono-fallback+input:mono-fallback
set-default-sink alsa_output.usb-Android_LE910C1-NF_0123456789ABCDEF-04.mono-fallback
set-default-source alsa_input.usb-Android_LE910C1-NF_0123456789ABCDEF-04.mono-fallback
```

The default.pa file also needs to be edited the same way it was for the Pool config and
the adjustment to the sample-rates.

**NOTE:** The name of 'usb-Android_LE910C1-NF_0123456789ABCDEF-04' can be different between different modem modules. Typically, the '-04' can change so make sure that
the modification of the 'default.pa' accounts for this difference.

### Baresip

The dialing script does not need to do any rerouting.

Edit the '.baresip/config' file to have the audio player set as shown below.

```bash
audio_driver            pulse
audio_player            pulse
audio_source            pulse
```

The file .baresip/accounts needs to have the following setup.

```bash
sip:6003@192.168.80.209;auth_user=6003;auth_pass=unsecurepassword;answermode=auto
```

**NOTE:** The client that runs on the target MUST be set to 'answermode=auto' for the
correct operation.

**NOTE:** some method of using authentication is needed because this is in the clear.

The service voip_call_monitor.service is responsible for starting the
voip_call_monitor_tcp.py script.

As root execute the following.

```bash
# Copy the service file to systemd directory
cp /mnt/data/voip_call_monitor.service /etc/systemd/system/.

# Reload systemd to recognize the new service
systemctl daemon-reload

# Enable the service to start on boot
systemctl enable voip_call_monitor.service

# Start the service now
systemctl start voip_call_monitor.service

# Check service status
systemctl status voip_call_monitor.service

# View logs
journalctl -u voip_call_monitor.service -f
```

### Asterisk

The asterisk server needs to know about the extensions in the '/etc/asterisk/pjsip.conf'
file.
An example is shown below.

```bash
[transport-udp]
type=transport
protocol=udp
bind=192.168.80.209:5060

[aor]
remove_existing=yes
qualify_frequency=180

[6001]
type=endpoint
context=from-internal
disallow=all
allow=ulaw
allow=alaw
auth=6001
aors=6001
direct_media=no
rtp_symmetric=yes
rewrite_contact=yes

[6003]
type=endpoint
context=from-internal
disallow=all
allow=ulaw
allow=alaw
auth=6003
aors=6003
direct_media=no

[6003]
type=auth
auth_type=userpass
password=unsecurepassword
username=6003

[6003]
type=aor
max_contacts=8
remove_existing=yes
qualify_frequency=180
```

**NOTE:** The authentication for the extensions loaded here need to match the
.baresip/accounts file.
**NOTE:** The passwords are in the clear!

The asterisk.service configuration needs to be modified to get it to start at boot
and handle calls. This is done by having a override.conf file in the
'/etc/systemd/system/asterisk.service.d/' directory.

```bash
cp asterisk.override.conf /etc/systemd/system/asterisk.service.d/override.conf
```

The contents of the override.conf file should be

```bash
# Then add these lines between the ### as explained at the top of the file.
[Unit]
Wants=network-online.target
After=network.target dev-ttyUSB2.device
Requires=dev-ttyUSB2.device

[Service]
ExecStartPre=/bin/sleep 10
```

As 'root' run the following once the asterisk files are in place.

```bash
systemctl enable asterisk
systemctl start asterisk
```



## Setup of Viking phone

Load the Viking IP Programming V1.5.0 tool.
On the IP Settings page, the following needs to be set
Server : <IP address of Gatework ethernet IP>
User Name: <extension setup on Asterisk for this phone>
Caller ID: <extension setup on Asterisk for this phone>
Password: <password from setup on Asterisk for this phone>

And on the Phone Settings page, the following needs to be set
"In-Band Audio Call Progress": Disabled
