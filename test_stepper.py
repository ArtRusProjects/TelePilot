"""
Unit-Tests für stepper.py.
"""

import sys
import types
import unittest


class StubPin:
    def __init__(self, pin, mode):
        self.pin = pin
        self.mode = mode
        self._value = 0
        self.calls = []

    def value(self, val=None):
        if val is None:
            return self._value
        self._value = val
        self.calls.append(val)


machine = types.ModuleType("machine")
machine.Pin = StubPin
machine.Pin.OUT = 1
machine.Pin.IN = 0

utime = types.ModuleType("utime")
utime.sleep_us = lambda _: None

time = types.ModuleType("time")
time.localtime = lambda *args: (2026, 5, 29, 23, 3, 33, 3, 149)
time.time = lambda: 0.0

sys.modules["machine"] = machine
sys.modules["utime"] = utime
sys.modules["time"] = time

import stepper


class TestStepper(unittest.TestCase):
    def test_negative_alt_fractional_steps_accumulate(self):
        rest = (0.0, 0.0)

        expected_rest = -0.3194444444444444
        for _ in range(3):
            rest = stepper.move_alt_az(-0.001, 0.0, delay_us=0, rest_steps=rest)
            self.assertAlmostEqual(rest[0], expected_rest, places=7)
            self.assertEqual(rest[1], 0.0)
            expected_rest -= 0.3194444444444444

        rest = stepper.move_alt_az(-0.001, 0.0, delay_us=0, rest_steps=rest)
        self.assertAlmostEqual(rest[0], -0.2777777777777778, places=7)
        self.assertEqual(rest[1], 0.0)

        self.assertEqual(len([v for v in stepper.step1.calls if v == 1]), 1)
        self.assertEqual(len([v for v in stepper.step2.calls if v == 1]), 0)


if __name__ == "__main__":
    unittest.main()
