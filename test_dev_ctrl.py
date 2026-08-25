import sys
import types
import unittest
import _thread


_thread.stack_size = lambda size: None


class _DummyPin:
    OUT = 0
    IN = 0
    PULL_UP = 0

    def __init__(self, *args, **kwargs):
        self._value = 1

    def value(self, *args):
        if args:
            self._value = args[0]
        return self._value


class _DummyRTC:
    _datetime = (2026, 7, 19, 0, 12, 0, 0, 0)

    @classmethod
    def datetime(cls, *args):
        if args:
            cls._datetime = args[0]
        return cls._datetime


machine_mod = types.ModuleType("machine")
machine_mod.RTC = _DummyRTC
machine_mod.Pin = _DummyPin
sys.modules.setdefault("machine", machine_mod)

utime_mod = types.ModuleType("utime")
utime_mod.sleep_us = lambda *_args, **_kwargs: None
sys.modules.setdefault("utime", utime_mod)

stepper_mod = types.ModuleType("stepper")
stepper_mod.move_alt_az = lambda *args, **kwargs: (0.0, 0.0)
stepper_mod.move_alt = lambda *args, **kwargs: None
stepper_mod.move_az = lambda *args, **kwargs: None
stepper_mod.slew_rate_to_us = lambda *_args, **_kwargs: 1000
sys.modules.setdefault("stepper", stepper_mod)

import dev_ctrl


class TestPrecessionHandling(unittest.TestCase):
    def test_ra_dec_to_alt_az_applies_precession_correction(self):
        device = dev_ctrl.dev_ctrl(
            utc_offset=2.0,
            latitude=49.68,
            longitude=8.62,
        )

        ra = "10:51:41.8"
        dec = "+08:13:06"

        alt, az = device.ra_dec_to_alt_az(ra, dec, apply_calibration=False)

        ra_deg = dev_ctrl.ra_to_deg(ra)
        dec_deg = dev_ctrl.dec_to_deg(dec)
        ra_corr, dec_corr = dev_ctrl.precession_correction(
            ra_deg, dec_deg, 2026 - 2000
        )
        _, (expected_alt, expected_az) = dev_ctrl.radec_to_altaz(
            ra_corr,
            dec_corr,
            device.get_localtime(),
            device.latitude,
            device.longitude,
            device.utc_offset,
        )

        self.assertAlmostEqual(alt, expected_alt, places=10)
        self.assertAlmostEqual(az, expected_az, places=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
