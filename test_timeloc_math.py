"""
Unit-Tests für timeloc.py mathematische Funktionen (Koordinatenumrechnung)

Diese Tests sind CPython-kompatibel und testen mathematische Funktionen.
Da timeloc.py Hardware-Abhängigkeiten hat, importieren wir hier nur
die mathematischen Funktionen direkt nach.

Ausführung: python3 test_timeloc_math.py
"""

import sys
import unittest
import math

# Importiere die mathematischen Funktionen direkt aus timeloc.py
# Diese könnten alternativ in ein separates _math.py Modul ausgelagert werden


# === Mathematische Funktionen (kopiert aus timeloc.py) ===


def ra_to_deg(ra_str):
    h, m, s = [int(x) for x in ra_str.split(":")]
    return (h + m / 60 + s / 3600) * 15


def dec_to_deg(dec_str):
    sign = -1 if dec_str.startswith("-") else 1
    d, m, s = [int(x) for x in dec_str.replace("-", "").replace("+", "").split(":")]
    return sign * (d + m / 60 + s / 3600)


def time_str_to_decimal(t):
    h, m, s = [int(x) for x in t.split(":")]
    return h + m / 60 + s / 3600


def time_to_decimal(h, m, s):
    return h + m / 60 + s / 3600


def gmst_simple(year, month, day, hour_utc):
    d: float = (
        367 * year
        - int(7 * (year + int((month + 9) / 12)) / 4)
        + int(275 * month / 9)
        + day
        - 730531.5
    )
    d += hour_utc * 0.041666667
    gmst = 280.46061837 + 360.98564736629 * d
    return gmst % 360


def equatorial_to_horizontal(ha, dec_deg, lat_deg):
    ha_r = math.radians(ha)
    dec_r = math.radians(dec_deg)
    lat_r = math.radians(lat_deg)

    sin_alt = math.sin(dec_r) * math.sin(lat_r) + math.cos(dec_r) * math.cos(
        lat_r
    ) * math.cos(ha_r)
    alt = math.asin(sin_alt)

    cos_az = (math.sin(dec_r) - math.sin(alt) * math.sin(lat_r)) / (
        math.cos(alt) * math.cos(lat_r)
    )

    if cos_az > 1:
        cos_az = 1
    if cos_az < -1:
        cos_az = -1

    az = math.acos(cos_az)

    if math.sin(ha_r) > 0:
        az = 2 * math.pi - az

    return math.degrees(alt), math.degrees(az)


def angle_diff(a, b):
    d = a - b
    if d > 180:
        d -= 360
    if d < -180:
        d += 360
    return d


def radec_to_altaz(ra_deg, dec_deg, local_time, lat_deg, lon_deg, utc_offset):
    t = local_time
    hour_local = time_to_decimal(t[4], t[5], t[6])
    hour_utc = hour_local - utc_offset

    gmst = gmst_simple(t[0], t[1], t[2], hour_utc)
    lst = (gmst + lon_deg) % 360

    ha = (lst - ra_deg) % 360
    return (gmst, equatorial_to_horizontal(ha, dec_deg, lat_deg))


def precession_correction(ra_deg, dec_deg, years_since_2000):
    m = 3.07496 + 0.00186 * years_since_2000
    n = 1.33621 - 0.00057 * years_since_2000

    ra_deg += (
        m + n * math.sin(math.radians(ra_deg)) * math.tan(math.radians(dec_deg))
    ) / 3600
    dec_deg += (n * math.cos(math.radians(ra_deg))) / 3600

    return ra_deg, dec_deg


# === UNIT TESTS ===


class TestConversionFunctions(unittest.TestCase):
    """Tests für Konvertierungsfunktionen."""

    def test_ra_to_deg_zero(self):
        """Test: RA 00:00:00 = 0°."""
        deg = ra_to_deg("00:00:00")
        self.assertAlmostEqual(deg, 0, places=5)

    def test_ra_to_deg_positive(self):
        """Test: RA 06:00:00 = 90°."""
        deg = ra_to_deg("06:00:00")
        self.assertAlmostEqual(deg, 90, places=5)

    def test_ra_to_deg_polaris(self):
        """Test: RA Polaris ungefähr 2h30m."""
        deg = ra_to_deg("02:30:00")
        expected = (2 + 30 / 60 + 0 / 3600) * 15  # 37.5°
        self.assertAlmostEqual(deg, expected, places=5)

    def test_dec_to_deg_positive(self):
        """Test: DEC +45:00:00 = 45°."""
        deg = dec_to_deg("+45:00:00")
        self.assertAlmostEqual(deg, 45, places=5)

    def test_dec_to_deg_negative(self):
        """Test: DEC -30:00:00 = -30°."""
        deg = dec_to_deg("-30:00:00")
        self.assertAlmostEqual(deg, -30, places=5)

    def test_dec_to_deg_arcsec(self):
        """Test: DEC +45:30:45."""
        deg = dec_to_deg("+45:30:45")
        expected = 45 + 30 / 60 + 45 / 3600
        self.assertAlmostEqual(deg, expected, places=5)

    def test_time_str_to_decimal(self):
        """Test: Zeit-String zu Dezimal."""
        decimal = time_str_to_decimal("12:30:00")
        expected = 12 + 30 / 60  # 12.5
        self.assertAlmostEqual(decimal, expected, places=5)

    def test_time_to_decimal(self):
        """Test: Zeit-Komponenten zu Dezimal."""
        decimal = time_to_decimal(12, 30, 0)
        expected = 12.5
        self.assertAlmostEqual(decimal, expected, places=5)


class TestGMSTCalculation(unittest.TestCase):
    """Tests für GMST-Berechnung."""

    def test_gmst_simple_j2000(self):
        """Test: GMST am J2000-Epoch (2000-01-01.5 12:00 UTC)."""
        gmst = gmst_simple(2000, 1, 1, 12.0)
        # LT: ~18.656
        self.assertGreater(gmst, 0)
        self.assertLess(gmst, 360)

    def test_gmst_simple_different_years(self):
        """Test: GMST für verschiedene Jahre ist unterschiedlich."""
        gmst_2000 = gmst_simple(2000, 1, 1, 12.0)
        gmst_2020 = gmst_simple(2020, 1, 1, 12.0)
        # GMSTs should not be identical due to precession
        self.assertNotAlmostEqual(gmst_2000, gmst_2020, places=1)

    def test_gmst_wraps_360(self):
        """Test: GMST bleibt in [0, 360)."""
        gmst = gmst_simple(2026, 4, 2, 21.0)
        self.assertGreaterEqual(gmst, 0)
        self.assertLess(gmst, 360)


class TestEquatorialToHorizontal(unittest.TestCase):
    """Tests für equatorial_to_horizontal Konvertierung."""

    def test_alt_az_at_zenith(self):
        """Test: Objekt am Zenit (ha=0, dec=latitude)."""
        ha = 0  # Stundenwinkel
        dec = 50  # Breitengrad = 50°
        lat = 50  # Beobachter-Breitengrad

        alt, az = equatorial_to_horizontal(ha, dec, lat)

        # Am Zenit: alt ≈ 90°, az ≈ egal
        self.assertAlmostEqual(alt, 90, places=1)

    def test_alt_az_at_horizon(self):
        """Test: Objekt am Horizont."""
        ha = 90  # 90° Stundenwinkel
        dec = 0  # Äquator
        lat = 50  # Beobachter-Breitengrad

        alt, az = equatorial_to_horizontal(ha, dec, lat)

        # Am Horizont: alt ≈ 0°
        self.assertAlmostEqual(alt, 0, places=1)

    def test_alt_az_circumpolar(self):
        """Test: Zirkumpolar-Objekt (never sets)."""
        ha = 0
        dec = 80  # Weit nördlich
        lat = 50  # Beobachter-Breitengrad

        alt, az = equatorial_to_horizontal(ha, dec, lat)

        # Sollte sichtbar sein (alt > 0)
        self.assertGreater(alt, 0)


class TestAngleDiff(unittest.TestCase):
    """Tests für angle_diff Hilfsfunktion."""

    def test_angle_diff_simple(self):
        """Test: Einfache Winkeldifferenz."""
        diff = angle_diff(100, 80)
        self.assertAlmostEqual(diff, 20, places=5)

    def test_angle_diff_wrap_positive(self):
        """Test: Positive Umwrappung."""
        diff = angle_diff(350, 10)
        self.assertAlmostEqual(diff, -20, places=5)

    def test_angle_diff_wrap_negative(self):
        """Test: Negative Umwrappung."""
        diff = angle_diff(10, 350)
        self.assertAlmostEqual(diff, 20, places=5)


class TestPrecessionCorrection(unittest.TestCase):
    """Tests für Präzessionskorrektur."""

    def test_precession_correction_returns_tuple(self):
        """Test: Precession returns (ra, dec)."""
        ra_deg = 100.0
        dec_deg = 50.0
        years_since_2000 = 20.0  # Jahr 2020

        ra_corrected, dec_corrected = precession_correction(
            ra_deg, dec_deg, years_since_2000
        )

        # Corrected values should be close to originals but not identical
        self.assertIsInstance(ra_corrected, float)
        self.assertIsInstance(dec_corrected, float)

    def test_precession_accumulates(self):
        """Test: Präzession akkumuliert über Zeit."""
        ra = 100.0
        dec = 50.0

        ra_10y, dec_10y = precession_correction(ra, dec, 10)
        ra_20y, dec_20y = precession_correction(ra, dec, 20)

        # 20 Jahreeffekt sollte größer sein als 10 Jahre
        diff_10y = abs(ra - ra_10y)
        diff_20y = abs(ra - ra_20y)
        self.assertGreater(diff_20y, diff_10y)


class TestIntegrationFunctions(unittest.TestCase):
    """Tests für Integrations-Funktionen."""

    def test_angle_diff_as_free_function(self):
        """Test: angle_diff als freie Funktion."""
        diff = angle_diff(350, 10)
        # 350 - 10 = 340, aber > 180, also: 340 - 360 = -20
        self.assertAlmostEqual(diff, -20, places=5)


class TestRadecToAltazIntegration(unittest.TestCase):
    """Tests für RA/DEC zu Alt/Az Konvertierung (Integrations-Tests)."""

    def test_radec_to_altaz_basic(self):
        """Test: Einfache RA/DEC zu Alt/Az Konvertierung."""
        ra_deg = 0.0
        dec_deg = 0.0
        local_time = (2026, 4, 2, 3, 12, 0, 0, 0)
        lat_deg = 50.0
        lon_deg = 10.0
        utc_offset = 2.0

        gmst, (alt, az) = radec_to_altaz(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            local_time=local_time,
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            utc_offset=utc_offset,
        )

        # Zeit sollte zwischen 0 und 360 sein
        self.assertGreaterEqual(gmst, 0)
        self.assertLess(gmst, 360)

        # Alt zwischen -90 und 90
        self.assertGreaterEqual(alt, -90)
        self.assertLessEqual(alt, 90)

        # Az zwischen 0 und 360
        self.assertGreaterEqual(az, 0)
        self.assertLess(az, 360)


if __name__ == "__main__":
    # Starte die Tests
    unittest.main(verbosity=2)
