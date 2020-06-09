import asyncio, time
from gpiozero import Motor, Button, TonalBuzzer, DistanceSensor, LineSensor
from rcute_servokit import ServoKit

import board
import digitalio
import adafruit_rgb_display.st7789 as st7789
from adafruit_rgb_display.rgb import color565

from subprocess import check_call, check_output
import yaml

class CozmarsServer:
    async def __aenter__(self):
        await self.lock.acquire()
        self.lmotor = Motor(*self.conf['motor']['left'])
        self.rmotor = Motor(*self.conf['motor']['right'])
        self.button = Button(self.conf['button'])
        self.buzzer = TonalBuzzer(self.conf['buzzer'])
        self.lir = LineSensor(self.conf['ir']['left'], queue_len=3, sample_rate=10)
        self.rir = LineSensor(self.conf['ir']['right'], queue_len=3, sample_rate=10)
        self.sonar = DistanceSensor(trigger=self.conf['sonar']['trigger'], echo=self.conf['sonar']['echo'], queue_len=5)

        self._sensor_event_queue = None
        self._button_last_press_time = 0
        def cb(ev, obj, attr):
            return lambda: self._sensor_event_queue and self.event_loop.call_soon_threadsafe(self._sensor_event_queue.put_nowait, (ev, getattr(obj, attr)))
        def button_press_cb():
            if self._sensor_event_queue:
                now = time.time()
                if now - self._button_last_press_time <= self._double_press_max_interval:
                    ev = 'double_pressed'
                else:
                    ev = 'pressed'
                self.event_loop.call_soon_threadsafe(self._sensor_event_queue.put_nowait, (ev, True))
                self._button_last_press_time = now
        self.lir.when_line = self.lir.when_no_line = cb('lir', self.lir, 'value')
        self.rir.when_line = self.rir.when_no_line = cb('rir', self.rir, 'value')
        self.button.when_pressed = button_press_cb
        self.button.when_released = cb('pressed', self.button, 'is_pressed')
        self.button.when_held = cb('held', self.button, 'is_held')
        self.sonar.when_in_range = cb('in_range', self.sonar, 'distance')
        self.sonar.when_out_of_range = cb('out_of_range', self.sonar, 'distance')
        self.screen_backlight.fraction = .1

        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.__del__()
        self.lock.release()

    def __del__(self):
        self.stop_all_motors()
        for a in [self.sonar, self.lir, self.rir, self.button, self.buzzer, self.lmotor, self.rmotor]:
            a.close()
        self.screen_backlight.fraction = None

    def __init__(self, config_path='../config.yml'):
        with open(config_path) as f:
            self.conf = yaml.safe_load(f)

        self.lock = asyncio.Lock()
        self.event_loop = asyncio.get_running_loop()

        self.servokit = ServoKit(channels=16, freq=self.conf['servo']['freq'])

        def conf_servo(servokit, conf):
            servo = servokit.servo[conf['channel']]
            servo.set_pulse_width_range(conf['min_pulse'], conf['max_pulse'])
            return servo

        self.larm = conf_servo(self.servokit, self.conf['servo']['right_arm'])
        self.rarm = conf_servo(self.servokit, self.conf['servo']['left_arm'])
        self._head = conf_servo(self.servokit, self.conf['servo']['head'])
        self._head.set_actuation_range(-30, 30)

        self.screen_backlight = self.servokit.servo[self.conf['servo']['backlight']['channel']]
        self.screen_backlight.set_pulse_width_range(0, 1000000//self.conf['servo']['freq'])
        spi = board.SPI()
        cs_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["screen"]["cs"]}'))
        dc_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["screen"]["dc"]}'))
        reset_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["screen"]["rst"]}'))
        self.screen = st7789.ST7789(spi, rotation=90, width=135, height=240, x_offset=53, y_offset=40,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=24000000,
        )
        self.servo_update_rate = self.conf['servo']['update_rate']
        self._double_press_max_interval = .5

    def save_config(self, config_path='../config.yml'):
        with open(config_path, 'w') as f:
            yaml.safe_dump(self.conf, f, indent=2)

    def calibrate_servo(self, channel, min_pulse=None, max_pulse=None):
        for s in self.conf['servo'].values():
            if isinstance(s, dict) and s.get('channel')==channel:
                s['min_pulse'] = min_pulse
                s['max_pulse'] = max_pulse
        servo = self.servokit.servo[channel]
        servo.set_pulse_width_range(min_pulse or servo.min_pulse, max_pulse or servo.max_pulse)

    def config(self, name):
        def get_conf(conf, name):
            return conf[name[0]] if len(name)==1 else get_conf(conf[name[0]], name[1:])
        return get_conf(self.conf, name.split('.'))

    async def speed(self, speed=None, duration=None):
        if not speed:
            return self.lmotor.value, self.rmotor.value
        try:
            self.lmotor.value, self.rmotor.value = speed
        except TypeError:
            self.lmotor.value = self.rmotor.value = speed
        if duration:
            await asyncio.sleep(duration)
            self.lmotor.value = self.rmotor.value = 0

    def stop_all_motors(self):
        self.lmotor.value = self.rmotor.value = 0
        self.rarm.fraction = self.larm.fraction= self._head.angle = None

    async def backlight(self, *args):
        if not args:
            return self.screen_backlight.fraction or 0
        value = args[0]
        duration = speed = None
        try:
            duration = args[1]
            speed = args[2]
        except IndexError:
            pass
        if not (duration or speed):
            self.screen_backlight.fraction = value or 0
            return
        elif speed:
            if not 0 < speed <= 1 * self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {1*self.servo_update_rate}')
            duration = (value - self.screen_backlight.fraction)/speed
        steps = int(duration * self.servo_update_rate)
        interval = 1/self.servo_update_rate
        inc = (value-self.screen_backlight.fraction)/steps
        for _ in range(steps):
            await asyncio.sleep(interval)
            self.screen_backlight.fraction += inc


    async def lift(self, *args):
        if not args:
            return self.rarm.fraction
        height = args[0]
        if height == None:
            self.rarm.fraction = self.larm.fraction = None
            return
        if not 0<= height <= 1:
            raise ValueError('Height must be 0 to 1')
        duration = speed = None
        try:
            duration = args[1]
            speed = args[2]
        except IndexError:
            pass
        if not (speed or duration):
            self.rarm.fraction = height
            self.larm.fraction = height
            return
        elif speed:
            if not 0 < speed <= 1 * self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {1*self.servo_update_rate}')
            duration = (height - self.larm.fraction)/speed
        if duration and self.larm.fraction:
            steps = int(duration * self.servo_update_rate)
            interval = 1/self.servo_update_rate
            inc = (height-self.larm.fraction)/steps
            for _ in range(steps):
                await asyncio.sleep(interval)
                self.larm.fraction += inc
                self.rarm.fraction += inc

    async def head(self, *args):
        if not args:
            return self._head.angle
        angle = args[0]
        if angle == None:
            self._head.angle = None
            return
        if not -30 <= angle <= 30:
            raise ValueError('Angle must be -30 ~ 30')
        duration = speed = None
        try:
            duration = args[1]
            speed = args[2]
        except IndexError:
            pass
        if not (speed or duration):
            self._head.angle = angle
            return
        elif speed:
            if not 0 < speed <= 60 * self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {60*self.servo_update_rate}')
            duration = (angle - self._head.angle)/speed
        if duration and self._head.angle:
            steps = duration*self.servo_update_rate
            interval = 1/self.servo_update_rate
            inc = (angle-self.larm.fraction)/steps
            for _ in range(steps):
                await asyncio.sleep(interval)
                self._head.angle += inc

    def display(self, image_data, x, y, x1, y1):
        self.screen._block(x, y, x1, y1, image_data)

    def fill(self, color565, x, y, w, h):
        self.screen.fill_rectangle(x, y, w, h, color565)

    def pixel(self, x, y, color565):
        return self.screen.pixel(x, y, color565)

    def gif(self, gif, loop):
        #https://github.com/adafruit/Adafruit_CircuitPython_RGB_screen/blob/master/examples/rgb_screen_pillow_animated_gif.py
        raise NotImplemented

    async def play(self, *, request_stream):
        async for note in request_stream:
            self.buzzer.play(str(note)) if note else self.buzzer.stop()

    async def tone(self, note, duration=None):
        self.buzzer.play(str(note)) if note else self.buzzer.stop()
        if duration:
            await asyncio.sleep(duration)
            self.buzzer.stop()

    async def sensor_data(self):
        try:
            self._sensor_event_queue = asyncio.Queue()
            while True:
                yield await self._sensor_event_queue.get()
        except Exception as e:
            self._sensor_event_queue = None
            raise e

    def double_press_max_interval(self, *args):
        if args:
            self._double_press_max_interval = args[0]
        else:
            return self._double_press_max_interval

    def hold_repeat(self, *args):
        if args:
            self.button.hold_repeat = args[0]
        else:
            return self.button.hold_repeat

    def held_time(self, *args):
        if args:
            self.button.held_time = args[0]
        else:
            return self.button.held_time

    def threshold_distance(self, *args):
        if args:
            self.sonar.threshold_distance = args[0]
        else:
            return self.sonar.threshold_distance

    def max_distance(self, *args):
        if args:
            self.sonar.max_distance = args[0]
        else:
            return self.sonar.max_distance

    def distance(self):
        return self.sonar.distance

    def microphone_volumn(self, *args):
        if args:
            if 0 <= args[0] <= 100:
                check_output(f'amixer set Boost {args[0]}%'.split(' '))
            else:
                raise ValueError('volumn must be 0 ~ 100')
        else:
            a = check_output('amixer get Boost'.split(' '))
            return int(a[a.index(b'[') + 1 : a.index(b'%')])


    async def camera(self, width, height, framerate):
        import picamera, io, threading, time
        try:
            queue = asyncio.Queue(1)
            stop_ev = threading.Event()

            def bg_run(loop):
                nonlocal queue, stop_ev, width, height, framerate
                with picamera.PiCamera(resolution=(width, height), framerate=framerate) as cam:
                    # Camera warm-up time
                    time.sleep(2)
                    stream = io.BytesIO()
                    for _ in cam.capture_continuous(stream, 'jpeg', use_video_port=True):
                        stream.seek(0)
                        loop.call_soon_threadsafe(queue.put_nowait, stream.read())
                        # queue.put_nowait(stream.read())
                        stream.seek(0)
                        stream.truncate()
                        if stop_ev.isSet():
                            break

            loop = asyncio.get_running_loop()
            # threading.Thread(target=bg_run, args=[loop]).start()
            bg_task = loop.run_in_executor(None, bg_run, loop)

            while True:
                yield await queue.get()

        finally:
            stop_ev.set()
            await bg_task

    async def microphone(self, samplerate=16000, dtype='int16'):
        import sounddevice as sd
        blocksize_sec = .1
        channels = 1
        # bytes_per_sample = dtype[-2:]//8
        # blocksize = int(blocksize_sec * channels * samplerate * bytes_per_sample)
        blocksize = int(blocksize_sec * channels * samplerate)
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue(5)
        def cb(indata, frames, time, status):
            nonlocal queue, loop
            if status:
                print(status, file=sys.stderr)
                raise sd.CallbackAbort
            loop.call_soon_threadsafe(queue.put_nowait, bytes(indata))

        with sd.RawInputStream(callback=cb, samplerate=samplerate, blocksize=blocksize, channels=channels, dtype=dtype):
            while True:
                yield await queue.get()
