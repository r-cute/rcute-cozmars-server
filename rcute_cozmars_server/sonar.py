import RPi.GPIO as GPIO
import time
import threading

class Sonar: # one pin distance sensor
    def __init__(self, pin, max_distance, threshold_distance, inverval=.2):
        GPIO.setmode(GPIO.BCM)
        self._pin = pin
        self.max_distance = max_distance
        self.threshold_distance = threshold_distance
        self.inverval = inverval
        self._distance = max_distance
        self.when_in_range = self.when_out_of_range = None
        self._th = threading.Thread(target=self.run, daemon=True)
        self._run = True
        self._th.start()

    def __del__(self):
        self.close()

    def close(self):
        self._run = False
        self._th.join(3)

    def run(self):
        while self._run:
            time.sleep(self.inverval)
            self.get_distance()

    def get_distance(self):
        GPIO.setup(self._pin, GPIO.OUT)
        # set Trigger to HIGH
        GPIO.output(self._pin, False)
        time.sleep(0.000002)
        GPIO.output(self._pin, True)

        # set Trigger after 0.01ms to LOW
        time.sleep(0.00001)
        GPIO.output(self._pin, False)

        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        StartTime = StopTime = TriggerTime = time.time()

        # save StartTime
        while GPIO.input(self._pin) == 0:
            StartTime = time.time()
            if StartTime - TriggerTime > 0.01:
                return

        # save time of arrival
        while GPIO.input(self._pin) == 1:
            pass
        StopTime = time.time()

        # time difference between start and arrival
        TimeElapsed = StopTime - StartTime
        # multiply with the sonic speed (34300 cm/s)
        # and divide by 2, because there and back
        self._last_distance = self._distance
        self._distance = min(TimeElapsed * 171.5, self.max_distance)

        if self._distance > self.threshold_distance > self._last_distance:
            self.when_out_of_range and self.when_out_of_range()
        elif self._distance < self.threshold_distance < self._last_distance:
            self.when_in_range and self.when_in_range()

    @property
    def distance(self):
        return self._distance

