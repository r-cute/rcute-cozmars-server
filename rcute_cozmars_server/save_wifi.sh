sed -i "s/\(ssid=\"\).*\(\"\)/\1$1\2/;s/\(psk=\"\).*\(\"\)/\1$2\2/" /etc/wpa_supplicant/wpa_supplicant.conf
