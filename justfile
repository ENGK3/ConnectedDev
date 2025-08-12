
target := "172.20.10.120"

push:
    scp test_serial.py  root@{{target}}:/mnt/data/test_serial.py
    scp switch_detect.sh  root@{{target}}:/mnt/data/switch_detect.sh
    scp switch_mon.sh  root@{{target}}:/mnt/data/switch_mon.sh
    scp switch_mon.service  root@{{target}}:/mnt/data/switch_mon.service
    scp check_reg.py  root@{{target}}:/mnt/data/check_reg.py