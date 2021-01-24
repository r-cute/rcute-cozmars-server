# rcute-cozmars-server

Firmware for Cozmars V2

## Upgrades compared to [V1](https://github.com/r-cute/rcute-cozmars-server/tree/v1)

* buzzer is replaced by a speaker
* motors are slightly faster

## Setup

* `sudo raspi-config`
	* enable ssh, i2c, spi, camera, and disable serial.
	* then set rpi's host name as 'rcute-cozmars-xxxx', 'xxxx' being the last 4 digit of mac address.
	* set your locale.
	* memory split and set 128 or 256 for GPU (not sure if this is needed)
* enable microphone according to [adafruit article](https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test)
* enable i2s amp(speaker) according to adafruit article starting from ["Create asound.conf file" section](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/raspberry-pi-usage#create-asound-dot-conf-file-2712971-28)
* make rpi auto generate wifi hotspot when unable to connect to your wifi router, [this article from raspberryconnect](https://www.raspberryconnect.com/projects/65-raspberrypi-hotspot-accesspoints/158-raspberry-pi-auto-wifi-hotspot-switch-direct-connection) will help
* install required libs
	1. build portaudio from latest(2020 Dec) source for [a new bug fix](https://github.com/PortAudio/portaudio/pull/344)
		```
		wget https://github.com/PortAudio/portaudio/archive/master.zip
		unzip portaudio-master.zip
		cd portaudio-master
		./configure && make && sudo make install
		```
		in the future you can simply `apt install libportaudio2`
	2. install other libs
		```
		sudo apt install libtiff5 libopenjp2-7 python3-cffi python3-pip
		```

* install rcute-cozmars-server 
	```
	sudo python3 -m pip install rcute-cozmars-server==2.*
	mkdir ~/.cozmars
	wget https://raw.githubusercontent.com/r-cute/rcute-cozmars-server/master/conf.json -P ~/.cozmars
	wget https://raw.githubusercontent.com/r-cute/rcute-cozmars-server/master/env.json -P ~/.cozmars
	sudo wget https://raw.githubusercontent.com/r-cute/rcute-cozmars-server/master/cozmars.service -P /etc/systemd/system
	sudo systemctl enable cozmars.service
	sudo reboot
	```

## Electronic parts

* raspberry pi zero w
* 15cm cable 72° lens OV5647 camera
* 9g plastic blue servo X3
* PCA9685 16-channel servo driver with capacitor (bend straight the 90° pins)
* 1.14 inch color display
* 3v ~~15r/m~~ 20r/m N20 motor X2
* L298N motor driver
* infrared sensor X2
* ultrasonic distance sensor (3.3v compatible)
* 12mmx12mm button
* 112D on/off power button
* INMP441 microphone (use 90° pins)
* 3.7v battery (important: not 7.4v)
* ~~buzzer~~
* MAX98357 amp
* 35x20mm 8om 1w cavity speaker
* and many 10cm wires (use soft silicone wires to connect display)

![wiring](/wiring.png)

Some of the pins are interchangable if you configure `~/.cozmars/conf.json` file accordingly. But pins of spi/i2s/i2c buses can't be changed.

## License

This project is open sourced for educational purpose, Commercial usage is prohibited.

## Related stuff

* 3d model and build instructions: https://www.thingiverse.com/thing:4657644
* python sdk: https://github.com/r-cute/rcute-cozmars