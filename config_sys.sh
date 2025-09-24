cp /mnt/data/99-ignore-modemmanager.rules  /etc/udev/rules.d/99-ignore-modemmanager.rules
cp /mnt/data/switch_mon.service /etc/systemd/system/switch_mon.service

cp /mnt/data/pulse/daemon.conf /etc/pulse/daemon.conf

mkdir -p /home/kuser/.config/systemd/user
cp /mnt/data/pulse/pulseaudio.service /home/kuser/.config/systemd/user/pulseaudio.service

# systemctl stop weston.service
# systemctl disable weston.service
# systemctl stop connectcore-demo-server.service
# systemctl disable connectcore-demo-server.service

systemctl daemon-reload
systemctl enable switch_mon.service
# This must be done a kuser.
#systemctl --user enable pulseaudio.service


# Remount the /mnt/linux to be able to write to it.
# umount /mnt/linux
# mount /dev/mmcblk0p1 /mnt/linux

# mv /mnt/linux/zImage-ccimx6sbc.bin /mnt/linux/zImage-ccimx6sbc.bin.orig
# mv /lib/modules/5.15.71-dey-dey /lib/modules/old-5.15.71-dey-dey