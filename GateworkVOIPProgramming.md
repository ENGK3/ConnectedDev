
```
apt-get install baresip asterisk
```

/etc/pulse/default.pa has the following appended.
```
set-card-profile alsa_card.usb-Android_LE910C1-NF_0123456789ABCDEF-04 output:mono-fallback+input:mono-fallback
set-default-sink alsa_output.usb-Android_LE910C1-NF_0123456789ABCDEF-04.mono-fallback
set-default-source alsa_input.usb-Android_LE910C1-NF_0123456789ABCDEF-04.mono-fallback
```

The dialing script does not need to do any rerouting.

.baresip/config file must have the audio player set as shown below.

audio_driver            pulse
audio_player            pulse
audio_source            pulse

.baresip/accounts needs to have the following setup..
```
sip:6003@192.168.80.209;auth_user=6003;auth_pass=unsecurepassword;answermode=auto
```
Note some method of using authentication is needed because this is in the clear.


The server needs to know about the extensions in the /etc/asterisk/pjsip.conf file.
An example is shown below.

```
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




Note the authentication for the extensions loaded here need to match the .baresip/accounts file.


Note we need to get asterisk running at startup.



As root run the following once the asterisk files are in place.
```
systemctl enable asterisk
systemctl start asterisk
```


Setup of Viking phone.

Load the Viking IP Programming V1.5.0 tool.
On the IP Settings page, the following needs to be set
Server : <IP address of Gatework ethernet IP>
User Name: <extension setup on Asterisk for this phone>
Caller ID: <extension setup on Asterisk for this phone>
Password: <password from setup on Asterisk for this phone>

And on the Phone Settings page, the following needs to be set
"In-Band Audio Call Progress": Disabled

