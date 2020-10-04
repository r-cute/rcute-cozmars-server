import board
from adafruit_pca9685 import PCA9685

class ServoKit:
    def __init__(self, *, channels, freq, i2c=None, address=0x40, reference_clock_speed=25000000):
        if channels not in [8, 16]:
            raise ValueError("servo_channels must be 8 or 16!")
        self._items = [None] * channels
        self._channels = channels
        if i2c is None:
            i2c = board.I2C()
        self._pca = PCA9685(
            i2c, address=address, reference_clock_speed=reference_clock_speed
        )
        self._pca.frequency = freq
        self._servo = _Servo(self)

    @property
    def servo(self):
        return self._servo


class _Servo:
    def __init__(self, kit):
        self.kit = kit

    def __getitem__(self, servo_channel):

        num_channels = self.kit._channels
        if servo_channel >= num_channels or servo_channel < 0:
            raise ValueError("servo must be 0-{}!".format(num_channels - 1))
        servo = self.kit._items[servo_channel]
        if servo is None:
            servo = Servo(self.kit._pca.channels[servo_channel])
            self.kit._items[servo_channel] = servo
            return servo
        if isinstance(self.kit._items[servo_channel], Servo):
            return servo
        raise ValueError("Channel {} is already in use.".format(servo_channel))

    def __len__(self):
        return len(self.kit._items)

class Servo:
    def __init__(self, pwm_out, *, start_angle=0, end_angle=180, min_pulse=750, max_pulse=2250):
        self._pwm_out = pwm_out
        self._last_fraction = None
        self.set_pulse_width_range(min_pulse, max_pulse)
        self.set_actuation_range(start_angle, end_angle)

    def set_actuation_range(self, start_angle, end_angle):
        """map [start_angle, end_angle] to [min_pulse, max_pulse]"""
        self._start_angle = start_angle
        self._end_angle = end_angle
        self._angle_range = end_angle - start_angle

    def set_pulse_width_range(self, min_pulse=750, max_pulse=2250):
        """Change min and max pulse widths."""
        self._min_pulse, self._max_pulse = min_pulse, max_pulse
        self._min_duty = int((min_pulse * self._pwm_out.frequency) / 1000000 * 0xFFFF)
        max_duty = (max_pulse * self._pwm_out.frequency) / 1000000 * 0xFFFF
        self._duty_range = int(max_duty - self._min_duty)

    @property
    def channel(self):
        return self._pwm_out._index

    @property
    def min_pulse(self):
        return self._min_pulse

    @property
    def max_pulse(self):
        return self._max_pulse

    @property
    def fraction(self):
        """Pulse width expressed as fraction between 0.0 (`min_pulse`) and 1.0 (`max_pulse`).
        For conventional servos, corresponds to the servo position as a fraction
        of the actuation range. Is None when servo is diabled (pulsewidth of 0ms).
        """
        if self._pwm_out.duty_cycle == 0 and self._min_duty != 0:  # Special case for disabled servos
            return self._last_fraction
        return ((self._pwm_out.duty_cycle - self._min_duty) / self._duty_range)

    @fraction.setter
    def fraction(self, value):
        if value is None:
            self._pwm_out.duty_cycle = 0  # disable the motor
            self._last_fraction = None
            return
        if not 0.0 <= value <= 1.0:
            raise ValueError("Must be 0.0 to 1.0")
        duty_cycle = self._min_duty + int(value * self._duty_range)
        self._pwm_out.duty_cycle = duty_cycle

    @property
    def angle(self):
        """The servo angle in degrees. Must be in the range ``0`` to ``actuation_range``.
        Is None when servo is disabled."""
        if self.fraction is None:  # special case for disabled servos
            return None
        return self._angle_range * self.fraction + self._start_angle

    @angle.setter
    def angle(self, new_angle):
        if new_angle is None:  # disable the servo by sending 0 signal
            self.fraction = None
            return
        if (self._start_angle <= new_angle <= self._end_angle) or (self._start_angle >= new_angle >= self._end_angle):
            self.fraction = (new_angle - self._start_angle) / self._angle_range
        else:
            raise ValueError("Angle out of range")

    def relax(self):
        self._last_fraction = self.fraction
        self._pwm_out.duty_cycle = 0
