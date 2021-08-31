from sys import argv
import uuid, os
from subprocess import check_call

def cmd(a):
    check_call(a.split())

if len(argv) >1:
    SERIAL = argv[1]
else:
    MAC = hex(uuid.getnode())[2:]
    SERIAL = MAC[-4:]
    # MAC = ':'.join([MAC[i:i+2] for i in range(0,12,2)])

os.system('rm /usr/local/lib/python3.7/dist-packages/rcute_cozmars_server/static/splash.png')

# set hostname and pi user passwd
cmd(f'raspi-config nonint do_hostname rcute-cozmars-{SERIAL}')
os.system(f"(echo \"{SERIAL}{SERIAL}\" ; echo \"{SERIAL}{SERIAL}\" ) | sudo passwd pi")

# wifi hotspot
cmd(f"sed -i -e s/ssid=.*$/ssid=rcute-cozmars-{SERIAL}/g /etc/hostapd/hostapd.conf")
cmd(f"sed -i -e s/wpa_passphrase=.*$/wpa_passphrase={SERIAL}{SERIAL}/g /etc/hostapd/hostapd.conf")

# default wifi to connect to
cmd("sed -i -e s/ssid=.*$/ssid=\"wifi_name\"/g /etc/wpa_supplicant/wpa_supplicant.conf")
cmd("sed -i -e s/psk=.*$/psk=\"wifi_password\"/g /etc/wpa_supplicant/wpa_supplicant.conf")

# expand file system
cmd('raspi-config nonint do_expand_rootfs')

