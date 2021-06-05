import numpy as np
import cv2
from PIL import Image, ImageFont, ImageDraw

font_color = '#00ffff'
font_file = '../rcute-cozmars/rcute_cozmars/resources/msyh.ttc'
bfont = ImageFont.truetype(font_file, 30)
sfont = ImageFont.truetype(font_file, 18)

# poweroff
image = Image.new("RGB", (240,135))
draw = ImageDraw.Draw(image)
draw.text((60,20), '正在重启', fill=font_color, font=bfont)
draw.text((55,75), '大约需要一分钟', fill=font_color, font=sfont)

image.save('./rcute_cozmars_server/static/reboot.png')

# reboot
image = Image.new("RGB", (240,135))
draw = ImageDraw.Draw(image)
draw.text((60,20), '正在关机', fill=font_color, font=bfont)
draw.text((45,65), '等内部黄灯熄灭后', fill=font_color, font=sfont)
draw.text((45,90), '再按下电源键断电', fill=font_color, font=sfont)

image.save('./rcute_cozmars_server/static/poweroff.png')