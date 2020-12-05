# rcute-cozmars-server

Cozmars, the open source 3d pritable educational robot

```
sudo apt install libtiff5 ibopenjp2-7 libportaudio2 python3-cffi
pip install rcute-cozmars-server==1.*
cp conf.json /home/pi/.cozmars.conf.json
cp env.json /home/pi/.cozmars.env.json
sudo cp cozmars.service /etc/systemd/system
sudo systemctl enable cozmars.service
```

![wiring](/wiring.png)

* 3d model: https://www.thingiverse.com/thing:4657644
* python sdk: https://github.com/hyansuper/rcute-cozmars

# License:

This project is open sourced for educational purpose, Commercial usage is prohibited.
