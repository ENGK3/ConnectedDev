# Gateworks Venice Programming

## Setup

To be able to get to the system console on first powering up of the board, the JTAG debugger will be needed.
It will allow the system console to be presented to the PC as a serial port. The standard

# Connectivity

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

The internet connection is needed to add certain packages to the Ubuntu OS to be able to
implement the solution.

** Note ** the IP address that is assigned it will be useful later.

## Additional packages

The following packages need to be added to the filesystem on the Gatework module.

Be sure there is a functioning network interface before attempting to complete the following commands.

```base
apt-get install alsa-utils python3-serial microcom
```

## Push Pool phone scripts.

To be able to push the pool phone scripts to the Gateworks board a user needs to be
created
```bash
adduser nuser
```
And create the user with a password. REMEMBER the password.

To facilitate the copying of files,
```bash
 ssh-copy-id nuser@172.20.10.71
```

On the Gatworks target create the "/mnt/data/" directory.

```bash
mkdir /mnt/data
chmod ugo+w /mnt/data
```

The push the scripts.

```bash
just push
```

## Configuring the system to perform the Pool phone function.

```bash
cp imx8mm-venice-gw7xxx-0x-gw16157.dtbo /boot/.

reboot
```

Hit the "Enter key several times while the UBoot screen is present to suspend the boot process,
a boot script variable needs to be modified to add the overlays needed.

```bash
setenv fdt_overlays "imx8mm-venice-gw7xxx-0x-gpio.dtbo imx8mm-venice-gw7xxx-0x-gw16157.dtbo"
saveenv
boot
```

Once the target has completed the boot process, the following script can be run to
set up the service for the pool phone application.





DTS Overlay.
cat << EOF > arch/arm64/boot/dts/freescale/imx8mm-venice-gw7xxx-0x-gpio.dts
/*
 * GW72xx GPIO:
 *  - repurpose ecspi2 CLK/MISO/MOSI/CS0 as GPIO
 *  - repurpose i2c3 CLK/DATA as GPIO
 */

#include <dt-bindings/gpio/gpio.h>

#include "imx8mm-pinfunc.h"

/dts-v1/;
/plugin/;


&gpio5 {
        pinctrl-names = "default";
        pinctrl-0 = <&pinctrl_gpio5_hog>;

        /* gpio-hog nodes allow you to give gpios a name and a default state:
         *   define one of 'input', 'output-low', or 'output-high' properties
         */
        gpio5_io10 {
                gpio-hog;
                gpios = <10 GPIO_ACTIVE_HIGH>;
                input;
                line-name = "gpio5_io10";
        };

        gpio5_io11 {
                gpio-hog;
                gpios = <11 GPIO_ACTIVE_HIGH>;
                input;
                line-name = "gpio5_io11";
        };

        gpio5_io12 {
                gpio-hog;
                gpios = <12 GPIO_ACTIVE_HIGH>;
                input;
                line-name = "gpio5_io12";
        };

        gpio5_io13 {
                gpio-hog;
                gpios = <13 GPIO_ACTIVE_HIGH>;
                input;
                line-name = "gpio5_io13";
        };

        gpio5_io18 {
                gpio-hog;
                gpios = <18 GPIO_ACTIVE_HIGH>;
                input;
                line-name = "gpio5_io18";
        };

        gpio5_io19 {
                gpio-hog;
                gpios = <19 GPIO_ACTIVE_HIGH>;
                input;
                line-name = "gpio5_io19";
        };
};

&i2c3 {
        status = "disabled";
};

&ecspi2 {
        status = "disabled";
};

&iomuxc {
        /* pinmux: refer to IMX8M Reference Manuals for the bit configuration
         *  - the first definition comes from imx8mm-pinfunc.h and sets the
         *    pins NUX_CTL register and input select
         *  - the second definition sets the PAD_CTL register that configures
         *    things like drive strength, slew rate, pull-up, pull-down, and hysteresis.
         *    If you want to be able to read back the pin state you need to set the SION
         *    bit by setting bit 30 (as is done below)
         */
        pinctrl_gpio5_hog: gpio5hoggrp {
                fsl,pins = <
                        MX8MM_IOMUXC_ECSPI2_SCLK_GPIO5_IO10     0x40000146 /* SION, pull-up, 6x drive str */
                        MX8MM_IOMUXC_ECSPI2_MOSI_GPIO5_IO11     0x40000106 /* SION, pull-down, 6x drive str */
                        MX8MM_IOMUXC_ECSPI2_MISO_GPIO5_IO12     0x40000006 /* SION, 6x drive-str */
                        MX8MM_IOMUXC_ECSPI2_SS0_GPIO5_IO13      0x40000146
                        MX8MM_IOMUXC_I2C3_SCL_GPIO5_IO18        0x40000146
                        MX8MM_IOMUXC_I2C3_SDA_GPIO5_IO19        0x40000146
                >;
        };
};
EOF