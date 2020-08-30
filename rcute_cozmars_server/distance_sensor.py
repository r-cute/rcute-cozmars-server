import RPi.GPIO as GPIO
import time
import threading

class DistanceSensor:
    def __init__(self, trigger, echo, max_distance, threshold_distance, inverval=.1, **kw):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(trigger, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
        self.trigger = trigger
        self.echo = echo
        self.max_distance = max_distance
        self.threshold_distance = threshold_distance
        self.inverval = inverval
        self._distance = max_distance
        self.when_in_range = self.when_out_of_range = None
        self.th = threading.Thread(target=self.run, daemon=True)
        self._run = True
        self.th.start()

    def __del__(self):
        self.close()

    def close(self):
        self._run = False
        self.th.join(10)

    def run(self):
        while self._run:
            time.sleep(self.inverval)
            self.get_distance()

    def get_distance(self):
        # set Trigger to HIGH
        GPIO.output(self.trigger, True)

        # set Trigger after 0.01ms to LOW
        time.sleep(0.00001)
        GPIO.output(self.trigger, False)

        StartTime = StopTime = TriggerTime = time.time()

        # save StartTime
        while GPIO.input(self.echo) == 0:
            StartTime = time.time()
            if StartTime - TriggerTime > 0.001:
                return

        # save time of arrival
        while GPIO.input(self.echo) == 1:
            pass
        StopTime = time.time()

        # time difference between start and arrival
        TimeElapsed = StopTime - StartTime
        # multiply with the sonic speed (34300 cm/s)
        # and divide by 2, because there and back
        self._last_distance = self._distance
        self._distance = min((TimeElapsed * 343) / 2, self.max_distance)

        if self._distance > self.threshold_distance > self._last_distance:
            self.when_out_of_range and self.when_out_of_range()
        elif self._distance < self.threshold_distance < self._last_distance:
            self.when_in_range and self.when_in_range()

    @property
    def distance(self):
        return self._distance

