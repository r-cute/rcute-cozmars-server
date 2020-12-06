# rcute-cozmars-server

Cozmars, the open source 3d pritable educational robot

* 3d model: https://www.thingiverse.com/thing:4657644
* python sdk: https://github.com/hyansuper/rcute-cozmars

```
sudo apt install libtiff5 ibopenjp2-7 libportaudio2 python3-cffi
pip install rcute-cozmars-server==1.*
cp conf.json /home/pi/.cozmars.conf.json
cp env.json /home/pi/.cozmars.env.json
sudo cp cozmars.service /etc/systemd/system
sudo systemctl enable cozmars.service
```

## Electronic parts

* raspberry pi zero w
* 15cm cable 72° lens OV5647 camera
* 9g plastic blue servo X3
* PCA9685 16-channel servo driver with capacitor (bend straight the 90° pins)
* 1.14 inch color display
* 3v 15r/m N20 motor X2
* L298N motor driver
* infrared sensor X2
* ultrasonic distance sensor (3.3v compatible)
* 12mmx12mm button
* 112D on/off power button
* INMP441 microphone (use 90° pins)
* 3.7v 6400mAh battery (important: not 7.4v)
* buzzer
* and many 10cm wires (use soft silicone wires to connect display)

![wiring](/wiring.png)

## License:

This project is open sourced for educational purpose, Commercial usage is prohibited.

