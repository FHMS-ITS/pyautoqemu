#!/bin/bash

# call script with ./launch.sh base_image qmp_port ssh_port vnc_port inst_media

# Backing Image
BASE_IMAGE=$1

# Port Forwarding
QMP_PORT=$2
SSH_PORT=$3
VNC_PORT=$4

INSTALL_MEDIA="path/to/install.img"

# UEFI firmware
# UEFI_SECBOOT="OVMF_CODE.secboot.fd"
UEFI_SECBOOT=$5
# UEFI_VARS="OVMF_VARS.fd"
UEFI_VARS=$6

# set up tpm emulator
rm -rf /tmp/mytpm1
mkdir /tmp/mytpm1
swtpm socket --tpmstate dir=/tmp/mytpm1 \
  --ctrl type=unixio,path=/tmp/mytpm1/swtpm-sock \
  --log level=0 & 


# defaults: 64 bit virtual machine and SLIRP networking

# outputs screen via vnc, listening on port 5900+1 (vnc=ip:port)
OPTS="-display vnc=:1"

# uses modern chipset virtualization and kvm acceleration
OPTS="$OPTS -enable-kvm"
OPTS="$OPTS -machine type=q35,accel=kvm"

# 4 processors
OPTS="$OPTS -smp 4" 

# 6gb ram
OPTS="$OPTS -m 6144"

# binds 'windows installation image' to cdrom
# OPTS="$OPTS -cdrom $INSTALL_MEDIA"

# attaches serial connection telnet or stdio
# OPTS="$OPTS -serial stdio"
# OPTS="$OPTS -serial telnet:127.0.0.1:4443,server"

# generic vga graphics card
OPTS="$OPTS -vga std"

# flash: OVMF UEFI secureboot firmware - without secureboot Win11 won't boot
OPTS="$OPTS -drive if=pflash,format=raw,readonly,file=$UEFI_SECBOOT"
# flash: OVMF writable UEFI vars
OPTS="$OPTS -drive if=pflash,format=raw,file=$UEFI_VARS"

# TPM - without TPM Win11 won't boot
OPTS="$OPTS -chardev socket,id=chrtpm,path=/tmp/mytpm1/swtpm-sock"
OPTS="$OPTS -tpmdev emulator,id=tpm0,chardev=chrtpm"
OPTS="$OPTS -device tpm-tis,tpmdev=tpm0"

# attach usb hxci controller with 'usb tablet device' on it to allow absolute input coordinates
# https://qemu-project.gitlab.io/qemu/system/devices/usb.html
# id=xhci leads to a bus named xhci.0
OPTS="$OPTS -device qemu-xhci,id=xhci"
OPTS="$OPTS -device usb-tablet,bus=xhci.0"

# prepare for adding a usb disk
#OPTS="$OPTS -device nec-usb-xhci,id=usbxhci"
# only works once with qmp, as device_del removes the drive and qmp has no drive_add functionality
#OPTS="$OPTS -drive if=none,id=stick,format=raw,file=/home/ls/code/tmp-usb.raw"

# binds QMP to socket
OPTS="$OPTS -qmp tcp:127.0.0.1:$QMP_PORT,server,nowait"

# binds SSH port of the guest to port 10022 on host
OPTS="$OPTS -net user,hostfwd=tcp::$SSH_PORT-:22" 
OPTS="$OPTS -net nic,id=eth1" 

# german keyboard layout
OPTS="$OPTS -k de" 

# monitor shell
OPTS="$OPTS -monitor telnet::45454,server,nowait" 

# enable vmx 
OPTS="$OPTS -cpu host" 
#OPTS="$OPTS -cpu qemu64,+vmx" 

# set hardware time
OPTS="$OPTS -rtc base=localtime"

echo $OPTS
echo $BASE_IMAGE

exec qemu-system-x86_64 $OPTS $BASE_IMAGE
