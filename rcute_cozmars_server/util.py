from os import path
from PIL import Image, ImageFont, ImageDraw
import gettext, locale, re
import asyncio

PKG = path.dirname(__file__)
STATIC = path.join(PKG, 'static')

def static(file_name):
    return path.join(STATIC, file_name)

def pkg(file_name):
    return path.join(PKG, file_name)

try:
    loc = gettext.translation('base', localedir=path.join(PKG, "locales"), languages=[locale.getdefaultlocale()[0]])
    loc.install()
    _ = loc.gettext
    _gettext = loc.gettext
except Exception as e:
    _ = gettext.gettext
    _gettext = gettext.gettext

def replace_gettext(match):
    match = match.group(2)
    return _gettext(match)

def parsed_template(name, **kwargs):
    with open(static("{}.html".format(name))) as file:
        content = file.read()
        content = re.sub(r'(\{_\("(.*?)"\)\})', replace_gettext, content)
        content = content.format(**kwargs)
        return content

CONF = '/home/pi/.cozmars/conf.json'
ENV = '/home/pi/.cozmars/env.json'

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

def beep(server):
    with open(static('sine_800hz_16k_i8.raw'), 'rb') as f:
        d = f.read()
    q = asyncio.Queue()
    for _ in range(5):
        q.put_nowait(d)
    q.put_nowait(StopAsyncIteration())
    return server.speaker(16000, 'int8', 1600, request_stream=q)