import digitalio
from neopixel_write import neopixel_write

class SonarLeds:
    def __init__(self, pin):
        self._pin = digitalio.DigitalInOut(pin)
        self._pin.direction = digitalio.Direction.OUTPUT
        self._color = [(0,0,0),(0,0,0)] #BGR
        self._bright = [0,0]
        self._buffer = bytearray(3), bytearray(3)
        self._update()

    @property
    def brightness(self):
        return self._bright

    @brightness.setter
    def brightness(self, br):
        for i in range(2):
            if br[i] is not None:
                self._bright[i] = br[i]
        self._update()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        for i in range(2):
            if c[i] is not None:
                self._color[i] = c[i]
        self._update()

    def deinit(self):
        self.brightness = 0, 0
        self._pin.deinit()

    def __del__(self):
        self.deinit()

    def _update(self):
        for buf, c, br in zip(self._buffer, self._color, self._bright):
            # bgr -> grb
            buf[0] = int(c[1] * br)
            buf[1] = int(c[2] * br)
            buf[2] = int(c[0] * br)
        neopixel_write(self._pin, self._buffer[0]*3+self._buffer[1]*3)