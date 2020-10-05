from os import path
from PIL import Image, ImageFont, ImageDraw

PKG = path.dirname(__file__)
STATIC = path.join(PKG, 'static')

def static(file_name):
    return path.join(STATIC, file_name)

def pkg(file_name):
    return path.join(PKG, file_name)

CONF = '/home/pi/.cozmars.json'

import socket
IP = socket.gethostbyname(f'{socket.gethostname()}.local')
HOSTNAME = socket.gethostname()

import uuid
MAC = hex(uuid.getnode())[2:]
SERIAL = MAC[-4:]
MAC = ':'.join([MAC[i:i+2] for i in range(0,12,2)])

def poweroff_screen():
    return Image.open(static('poweroff.png'))

def reboot_screen():
    return Image.open(static('reboot.png'))

def splash_screen():
    splash = static('splash.png')
    if not path.isfile(splash):
        font_color = '#00ffff'
        font_file = static('DejaVuSans.ttf')
        bfont = ImageFont.truetype(font_file, 30)
        sfont = ImageFont.truetype(font_file, 25)

        image = Image.new("RGB", (240,135))
        draw = ImageDraw.Draw(image)
        draw.text((55,27), 'Cozmars', fill=font_color, font=bfont)
        draw.text((85,72), SERIAL, fill=font_color, font=sfont)

        image.save(splash)

    return Image.open(splash)