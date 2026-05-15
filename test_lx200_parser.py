"""
Unit-Tests für lx200_parser.py

Diese Tests sind CPython-kompatibel und testen alle Parse- und Format-Funktionen.
Ausführung: python3 test_lx200_parser.py
"""

import sys
import types
import unittest


class StubLogger:
    """Stub für das Logger-Modul, damit das Modul ohne MicroPython lädt."""

    def __init__(self, name):
        pass

    def debug(self, *args):
        pass

    def info(self, *args):
        pass

    def error(self, *args):
        pass


class StubRTC:
    def __init__(self):
        self._dt = (2026, 4, 2, 3, 21, 41, 59, 0)

    def datetime(self, *args):
        if args:
            self._dt = args[0]
        return self._dt


sys.modules["machine"] = types.ModuleType("machine")
sys.modules["machine"].RTC = StubRTC
sys.modules["network"] = types.ModuleType("network")
sys.modules["stepper"] = types.ModuleType("stepper")

sys.modules["stepper"].slew_rate_to_us = lambda slew_rate: 1000
sys.modules[
    "stepper"
].move_alt_az = lambda alt_angle, az_angle, delay_us=2000, rest_steps=(0, 0): (
    0.0,
    0.0,
)
sys.modules["stepper"].move_alt = lambda alt_angle, delay_us=1000: None
sys.modules["stepper"].move_az = lambda az_angle, delay_us=2000: None

sys.modules["_thread"] = types.ModuleType("_thread")
sys.modules["_thread"].stack_size = lambda size: None
sys.modules["_thread"].start_new_thread = lambda target, args: None

# Mock das Logger-Modul
sys.modules["logging"] = types.ModuleType("logging")
sys.modules["logging"].Logger = StubLogger

import timeloc as tl
import lx200_parser as lx200


class TestDateTimeParsing(unittest.TestCase):
    """Tests für Datums- und Zeit-Parsing."""

    def test_parse_date_valid(self):
        """Test: Gültiges Datum im Format MM/DD/YY."""
        year, month, day = lx200.parse_date("04/02/26")
        self.assertEqual(year, 2026)
        self.assertEqual(month, 4)
        self.assertEqual(day, 2)

    def test_parse_date_jan_01(self):
        """Test: 01.01.00 = 2000."""
        year, month, day = lx200.parse_date("01/01/00")
        self.assertEqual(year, 2000)
        self.assertEqual(month, 1)
        self.assertEqual(day, 1)

    def test_parse_time_valid(self):
        """Test: Gültige Zeit im Format HH:MM:SS."""
        h, m, s = lx200.parse_time("12:34:56")
        self.assertEqual(h, 12)
        self.assertEqual(m, 34)
        self.assertEqual(s, 56)

    def test_parse_time_midnight(self):
        """Test: Mitternacht 00:00:00."""
        h, m, s = lx200.parse_time("00:00:00")
        self.assertEqual(h, 0)
        self.assertEqual(m, 0)
        self.assertEqual(s, 0)


class TestCoordinateParsing(unittest.TestCase):
    """Tests für Koordinaten-Parsing (Breitengrad, Längengrad)."""

    def test_parse_lat_positive(self):
        """Test: Positiver Breitengrad (Norden)."""
        lat = lx200.parse_lat("+49*41")
        self.assertAlmostEqual(lat, 49 + 41 / 60, places=5)

    def test_parse_lat_negative(self):
        """Test: Negativer Breitengrad (Süden)."""
        lat = lx200.parse_lat("-33*52")
        expected = -(33 + 52 / 60)
        self.assertAlmostEqual(lat, expected, places=5)

    def test_parse_lon_valid(self):
        """Test: Längengrad Parsing."""
        lon = lx200.parse_lon("008*37")
        # 008°37' = 8 + 37/60, dann negiert wegen Konvention
        expected = -(8 + 37 / 60)
        self.assertAlmostEqual(lon, expected, places=5)

    def test_parse_lon_360_conversion(self):
        """Test: Längengrad > 180° wird zu negativem Winkel."""
        lon = lx200.parse_lon("351*36")
        # 351°36' = 351 + 36/60 = 351.6°
        # Umwandlung: 351.6 - 360 = -8.4°
        # Dann negiert: +8.4°
        expected = -(351 + 36 / 60 - 360)
        self.assertAlmostEqual(lon, expected, places=5)


class TestCoordinateFormatting(unittest.TestCase):
    """Tests für Koordinaten-Formatierung."""

    def test_format_lat_positive(self):
        """Test: Formatierung positiver Breitengrad."""
        result = lx200.format_lat(49.6833)  # 49°41'
        self.assertTrue(result.startswith("+"))
        self.assertTrue(result.endswith("#"))
        self.assertIn("49", result)

    def test_format_lat_negative(self):
        """Test: Formatierung negativer Breitengrad."""
        result = lx200.format_lat(-33.8667)  # -33°52'
        self.assertTrue(result.startswith("-"))
        self.assertTrue(result.endswith("#"))

    def test_format_lon_positive(self):
        """Test: Formatierung positiver Längengrad."""
        result = lx200.format_lon(-8.6167)  # -8°37' (negiert)
        self.assertTrue(result.endswith("#"))
        self.assertIn("008", result)

    def test_format_lon_negative(self):
        """Test: Formatierung negativer Längengrad."""
        result = lx200.format_lon(8.6167)  # +8°37' (negiert)
        self.assertTrue(result.endswith("#"))


class TestTimeFormatting(unittest.TestCase):
    """Tests für Zeit-Formatierung."""

    def test_format_time_lx200(self):
        """Test: Formatierung von localtime-Tuple."""
        # (year, month, day, weekday, hour, minute, second, yday)
        local_time = (2026, 4, 2, 3, 21, 41, 59, 0)
        result = lx200.format_time_lx200(local_time)
        self.assertEqual(result, "21:41:59#")

    def test_format_date_lx200(self):
        """Test: Formatierung von Datum aus localtime-Tuple."""
        local_time = (2026, 4, 2, 3, 21, 41, 59, 0)
        result = lx200.format_date_lx200(local_time)
        self.assertEqual(result, "04/02/26#")


class TestRaDecFormatting(unittest.TestCase):
    """Tests für RA/DEC-Formatierung."""

    def test_format_ra_lx200(self):
        """Test: RA-Formatierung."""
        result = lx200.format_ra_lx200("05:00:00")
        self.assertEqual(result, "05:00:00#")

    def test_format_dec_lx200_positive(self):
        """Test: DEC-Formatierung positiv."""
        result = lx200.format_dec_lx200("+20:00:00")
        self.assertIn("+20*00:00#", result)

    def test_format_dec_lx200_negative(self):
        """Test: DEC-Formatierung negativ."""
        result = lx200.format_dec_lx200("-16:43:42")
        self.assertIn("-16*43:42#", result)


class TestLX200State(unittest.TestCase):
    """Tests für die LX200State-Klasse."""

    def setUp(self):
        """Erstelle einen Mock timeloc."""

        class MockTimeloc:
            def __init__(self):
                self.latitude = 49.0
                self.longitude = -8.0
                self.utc_offset = 2.0

            def get_localtime(self):
                return (2026, 4, 2, 3, 21, 41, 59, 0)

            def ra_dec_to_alt_az(self, ra, dec):
                return 45.0, 90.0

            def update_rtc(self, *args):
                pass

            def set_utc_offset(self, offset):
                self.utc_offset = offset

            def set_loc(self, lat, lon):
                self.latitude = lat
                self.longitude = lon

        self.mock_timeloc = MockTimeloc()
        self.state = lx200.LX200State(self.mock_timeloc)

    def test_state_init(self):
        """Test: LX200State wird mit korrekten Defaults initialisiert."""
        self.assertIsNone(self.state.ra_target)
        self.assertIsNone(self.state.dec_target)
        self.assertEqual(self.state.current_ra, "05:00:00")
        self.assertEqual(self.state.current_dec, "+20:00:00")

    def test_state_ra_target_set(self):
        """Test: RA-Target kann gesetzt werden."""
        self.state.ra_target = "06:45:07"
        self.assertEqual(self.state.ra_target, "06:45:07")

    def test_state_dec_target_set(self):
        """Test: DEC-Target kann gesetzt werden."""
        self.state.dec_target = "-16:43:42"
        self.assertEqual(self.state.dec_target, "-16:43:42")


class TestAngleDiff(unittest.TestCase):
    """Tests für die Winkel-Differenz-Berechnung."""

    def test_angle_diff_normal(self):
        """Test: Normale Winkeldifferenz."""
        diff = lx200._angle_diff(90, 45)
        self.assertAlmostEqual(diff, 45, places=5)

    def test_angle_diff_wrap_positive(self):
        """Test: Positive Umwrappung (über 180°)."""
        diff = lx200._angle_diff(350, 10)
        # 350 - 10 = 340, aber > 180, also: 340 - 360 = -20
        self.assertAlmostEqual(diff, -20, places=5)

    def test_angle_diff_wrap_negative(self):
        """Test: Negative Umwrappung (unter -180°)."""
        diff = lx200._angle_diff(10, 350)
        # 10 - 350 = -340, aber < -180, also: -340 + 360 = 20
        self.assertAlmostEqual(diff, 20, places=5)

    def test_angle_diff_zero(self):
        """Test: Winkeldifferenz = 0."""
        diff = lx200._angle_diff(100, 100)
        self.assertAlmostEqual(diff, 0, places=5)


class TestHandleCommand(unittest.TestCase):
    """Tests für die LX200-Kommandoverarbeitung."""

    def setUp(self):
        """Erstelle einen Mock timeloc."""

        class MockTimeloc:
            def __init__(self):
                self.latitude = 49.68
                self.longitude = -8.62
                self.utc_offset = 2.0
                self.cont_mv = False
                self.cont_mv_step = False
                self.cont_mv_speed = 3

            def get_localtime(self):
                return (2026, 4, 2, 3, 21, 41, 59, 0)

            def ra_dec_to_alt_az(self, ra, dec):
                return 45.0, 90.0

            def update_rtc(self, *args):
                pass

            def set_utc_offset(self, offset):
                self.utc_offset = offset

            def set_loc(self, lat, lon):
                self.latitude = lat
                self.longitude = lon

            def stop_tracking(self):
                pass

            def start_tracking(self):
                pass

            def set_calibration_point(self):
                pass

            def start_cont_mv(self, dir):
                pass

            def movement_step(self, dir):
                pass

            def run_goto(self):
                pass

        self.mock_timeloc = MockTimeloc()
        self.state = lx200.LX200State(self.mock_timeloc)

    def test_handle_ka_command(self):
        """Test: 'Ka'-Befehl wird ignoriert."""
        result = lx200.handle_command("Ka", self.state)
        self.assertIsNone(result)

    def test_handle_init_command(self):
        """Test: '##'-Befehl."""
        result = lx200.handle_command("##", self.state)
        self.assertEqual(result, b"0#")

    def test_handle_handshake_command(self):
        """Test: '#\\x06'-Befehl."""
        result = lx200.handle_command("#\x06", self.state)
        self.assertEqual(result, b"P")

    def test_handle_gr_command(self):
        """Test: #:GR# (Get RA)."""
        result = lx200.handle_command("#:GR#", self.state)
        self.assertTrue(result.endswith(b"#"))
        self.assertIn(b"05:00:00", result)

    def test_handle_gd_command(self):
        """Test: #:GD# (Get DEC)."""
        result = lx200.handle_command("#:GD#", self.state)
        self.assertTrue(result.endswith(b"#"))
        self.assertIn(b"20", result)

    def test_handle_gvp_command(self):
        """Test: #:GVP# (Get Produkt-Bezeichnung)."""
        result = lx200.handle_command("#:GVP#", self.state)
        self.assertEqual(result, b"TelePico#")

    def test_handle_gvn_command(self):
        """Test: #:GVN# (Get Firmware-Version)."""
        result = lx200.handle_command("#:GVN#", self.state)
        self.assertEqual(result, b"1.0#")

    def test_handle_sr_command(self):
        """Test: #:Sr...# (Set RA)."""
        result = lx200.handle_command("#:Sr05:30:00#", self.state)
        self.assertEqual(result, b"1")
        self.assertEqual(self.state.ra_target, "05:30:00")

    def test_handle_sd_command(self):
        """Test: #:Sd...# (Set DEC)."""
        result = lx200.handle_command("#:Sd-15:45:30#", self.state)
        self.assertEqual(result, b"1")
        self.assertEqual(self.state.dec_target, "-15:45:30")

    def test_handle_sg_command(self):
        """Test: #:SG...# (Set UTC Offset)."""
        result = lx200.handle_command("#:SG-2.0#", self.state)
        self.assertEqual(result, b"1")
        self.assertAlmostEqual(self.mock_timeloc.utc_offset, 2.0, places=2)

    def test_handle_sl_command_valid(self):
        """Test: #:SL...# (Set Time) gültig."""
        result = lx200.handle_command("#:SL12:34:56#", self.state)
        self.assertEqual(result, b"1")
        self.assertEqual(self.state.pending_time, (12, 34, 56))
        self.assertTrue(self.state.time_set)

    def test_handle_sc_command_valid(self):
        """Test: #:SC...# (Set Date) gültig."""
        result = lx200.handle_command("#:SC04/15/26#", self.state)
        self.assertTrue(result.startswith(b"1"))
        self.assertEqual(self.state.pending_date, (2026, 4, 15))
        self.assertTrue(self.state.date_set)

    def test_handle_invalid_command(self):
        """Test: Ungültiger Befehl."""
        result = lx200.handle_command("#INVALID#", self.state)
        self.assertEqual(result, b"0#")


class TestTimelocCalibration(unittest.TestCase):
    """Tests für die 2-Stern-Kalibrierung in timeloc."""

    def setUp(self):
        self.tl = tl.timeloc()
        self.tl.latitude = 49.0
        self.tl.longitude = 8.0
        self.tl.utc_offset = 2

    def test_single_calibration_point_sets_offsets(self):
        ideal_alt, ideal_az = self.tl.ideal_alt_az("05:00:00", "+20:00:00")
        self.tl.add_calibration_point(
            "05:00:00", "+20:00:00", ideal_alt + 1.0, (ideal_az + 2.0) % 360
        )

        self.assertTrue(self.tl.is_calibrated)
        self.assertAlmostEqual(self.tl.calibration_model["alt_offset"], 1.0, places=5)
        self.assertAlmostEqual(self.tl.calibration_model["az_offset"], 2.0, places=5)

    def test_two_point_calibration_applies_average_offset(self):
        ideal_alt_1, ideal_az_1 = self.tl.ideal_alt_az("05:00:00", "+20:00:00")
        ideal_alt_2, ideal_az_2 = self.tl.ideal_alt_az("06:00:00", "+21:00:00")

        self.tl.add_calibration_point(
            "05:00:00", "+20:00:00", ideal_alt_1 + 1.0, (ideal_az_1 + 2.0) % 360
        )
        self.tl.add_calibration_point(
            "06:00:00", "+21:00:00", ideal_alt_2 + 1.0, (ideal_az_2 + 2.0) % 360
        )

        corrected_alt, corrected_az = self.tl.apply_calibration(ideal_alt_2, ideal_az_2)

        self.assertAlmostEqual(self.tl.calibration_model["alt_offset"], 1.0, places=5)
        self.assertAlmostEqual(self.tl.calibration_model["az_offset"], 2.0, places=5)
        self.assertAlmostEqual(corrected_alt, ideal_alt_2 + 1.0, places=5)
        self.assertAlmostEqual(corrected_az, (ideal_az_2 + 2.0) % 360, places=5)

    def test_ra_dec_to_alt_az_applies_calibration_if_enabled(self):
        ideal_alt, ideal_az = self.tl.ideal_alt_az("05:00:00", "+20:00:00")
        self.tl.add_calibration_point(
            "05:00:00", "+20:00:00", ideal_alt + 1.0, (ideal_az + 2.0) % 360
        )

        calibrated_alt, calibrated_az = self.tl.ra_dec_to_alt_az(
            "05:00:00", "+20:00:00"
        )

        self.assertAlmostEqual(calibrated_alt, ideal_alt + 1.0, places=5)
        self.assertAlmostEqual(calibrated_az, (ideal_az + 2.0) % 360, places=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
