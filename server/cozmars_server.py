import asyncio
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

        self.lir.when_line = self.lir.when_no_line = \
        self.rir.when_line = self.rir.when_no_line = \
        self.button.when_pressed = self.button.when_released = \
        self.sonar.when_in_range = self.sonar.when_out_of_range = \
            lambda: self.event_loop.call_soon_threadsafe(self.sensor_change_event.set)

    async def __aexit__(self, exc_type, exc, tb):
        self.__del__()
        for a in [self.sonar, self.lir, self.rir, self.button, self.buzzer, self.lmotor, self.rmotor]:
            a.close()
        self.lock.release()

    def __del__(self):
        self.stop_all_motors()
        self.backlight(0)

    def __init__(self, config_path='../config.yml'):
        with open(config_path) as f:
            self.conf = yaml.safe_load(f)

        self.lock = asyncio.Lock()
        self.sensor_change_event = asyncio.Event()
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

        self.display_backlight = self.servokit.servo[self.conf['servo']['backlight']['channel']]
        self.display_backlight.set_pulse_width_range(0, 1000000//self.conf['servo']['freq'])
        spi = board.SPI()
        cs_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["display"]["cs"]}'))
        dc_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["display"]["dc"]}'))
        reset_pin = digitalio.DigitalInOut(getattr(board, f'D{self.conf["display"]["rst"]}'))
        self.display = st7789.ST7789(spi, rotation=90, width=135, height=240, x_offset=53, y_offset=40,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=24000000,
        )
        self.servo_update_rate = self.conf['servo']['update_rate']

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

    def speed(self, *args):
        ln = len(args)
        if ln == 1:
            self.lmotor.value = self.rmotor.value = args[0]
        elif ln == 2:
            self.lmotor.value, self.rmotor.value = args

    def stop_all_motors(self):
        self.speed(0)
        self.rarm.fraction = self.larm.fraction= self._head.angle = None

    def backlight(self, fraction):
        self.display_backlight.fraction = fraction

    async def lift(self, height, duration=None, speed=None):
        if height == None:
            self.rarm.fraction = self.larm.fraction = None
            return
        if not 0<= height <= 1:
            raise ValueError('Height must be 0 to 1')
        if not (speed or duration):
            self.rarm.fraction = height
            self.larm.fraction = height
            return
        if speed and duration:
            raise Exception('cannot set both speed and duration')
        elif speed:
            if not 0 < speed <= 1 / self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {self.servo_update_rate}')
            duration = (height - self.larm.fraction)/speed
        if duration and self.larm.fraction:
            steps = int(duration * self.servo_update_rate)
            interval = 1/self.servo_update_rate
            inc = (height-self.larm.fraction)/steps
            for _ in range(steps):
                await asyncio.sleep(interval)
                self.larm.fraction += inc
                self.rarm.fraction += inc

    async def head(self, angle, duration=None, speed=None):
        if angle==None:
            self._head.angle=None
            return
        if not -30 <= angle <= 30:
            raise ValueError('Angle must be -30 ~ 30')
        if not (speed or duration):
            self._head.angle = angle
            return
        elif speed and duration:
            raise Exception('cannot set both speed and duration')
        elif speed:
            if not 0 < speed <= 60 / self.servo_update_rate:
                raise ValueError(f'Speed must be 0 ~ {60/self.servo_update_rate}')
            duration = (angle - self._head.angle)/speed
        if duration and self._head.angle:
            steps = duration*self.servo_update_rate
            interval = 1/self.servo_update_rate
            inc = (angle-self.larm.fraction)/steps
            for _ in range(steps):
                await asyncio.sleep(interval)
                self._head.angle += inc

    def image(self, image):
        self.display.image(image)

    def fill(self, rgb):
        self.display.fill(color565(rgb))

    def pixel(self, pos, rgb):
        self.display.pixel(pos[0], pos[1], color565(rgb))

    def gif(self, gif):
        #https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display/blob/master/examples/rgb_display_pillow_animated_gif.py
        pass

    async def tone(self, *, request_stream):
        async for t in request_stream:
            self.buzzer.play(str(t)) if t else self.buzzer.stop()

    async def sensor_data(self, *, request_stream):
        self.sensor_change_event.clear()
        while True:
            done, pending = await asyncio.wait({request_stream.get(), self.sensor_change_event.wait()}, return_when=asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()
            if self.sensor_change_event.is_set():
                self.sensor_change_event.clear()
            yield self.lir.value, self.rir.value, self.button.value, self.sonar.distance

    def distance_threshold(self, dist=None):
        if dist:
            self.sonar.threshold = dist
        else:
            return self.sonar.threshold

    def max_distance(self, dist=None):
        if dist:
            self.sonar.max_distance = dist
        else:
            return self.sonar.max_distance

    def rec_vol(self, vol=None):
        if vol:
            if 0 <= vol <= 100:
                check_output(f'amixer set Boost {vol}%'.split(' '))
            else:
                raise ValueError('volumn must be 0 ~ 100')
        else:
            a = check_output('amixer get Boost'.split(' '))
            return int(a[a.index(b'[') + 1 : a.index(b'%')])


    async def cam(self, width, height, framerate):
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

    async def mic(self, samplerate=16000):
        import sounddevice as sd
        dtype = 'int16'
        blocksize_sec = .1
        bytes_per_sample = 2
        channels = 1
        blocksize = int(blocksize_sec * bytes_per_sample * channels * samplerate)
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
