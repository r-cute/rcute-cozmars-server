from os import path

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
SERIAL = MAC[-5:-3]+MAC[-2:]
