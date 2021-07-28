# AgilisAGP Tange Device Server

Do not forget to set a udev.rule for the device.

SUBSYSTEM=="tty", ATTRS{idVendor}=="104d", ATTRS{idProduct}=="3006", ATTRS{serial}=="XXXXXXXXXX", SYMLINK+="ttyAGP1", MODE="0666"
