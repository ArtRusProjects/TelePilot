from machine import RTC
from logging import Logger
import math
import stepper
import _thread
import time

# import time

log = Logger("TimeLoc")

_thread.stack_size(5 * 1024)  # to avoid RuntimeError: maximum recursion depth exceeded

GMST_PER_SEC = 360.98564736629 / 86400.0


# -----------------------------
# Parsing
# -----------------------------
def ra_to_deg(ra_str):
    h, m, s = [int(x) for x in ra_str.split(":")]
    return (h + m / 60 + s / 3600) * 15


def dec_to_deg(dec_str):
    sign = -1 if dec_str.startswith("-") else 1
    d, m, s = [int(x) for x in dec_str.replace("-", "").replace("+", "").split(":")]
    return sign * (d + m / 60 + s / 3600)


def precession_correction(ra_deg, dec_deg, years_since_2000):
    m = 3.07496 + 0.00186 * years_since_2000
    n = 1.33621 - 0.00057 * years_since_2000

    ra_deg += (
        m + n * math.sin(math.radians(ra_deg)) * math.tan(math.radians(dec_deg))
    ) / 3600
    dec_deg += (n * math.cos(math.radians(ra_deg))) / 3600

    return ra_deg, dec_deg


def time_str_to_decimal(t):
    h, m, s = [int(x) for x in t.split(":")]
    return h + m / 60 + s / 3600


def time_to_decimal(h, m, s):
    return h + m / 60 + s / 3600


# -----------------------------
# GMST (ohne große Zahlen!)
# -----------------------------
def gmst_simple(year, month, day, hour_utc):
    d: float = (
        367 * year
        - int(7 * (year + int((month + 9) / 12)) / 4)
        + int(275 * month / 9)
        + day
        - 730531.5
    )
    # print("d vor:", d)
    # print("div:", hour_utc / 24.0)
    d += hour_utc * 0.041666667  # / 24.0
    # print("d nach:", d)

    gmst = 280.46061837 + 360.98564736629 * d
    return gmst % 360


# -----------------------------
# Hauptfunktionen
# -----------------------------
def radec_to_altaz(ra_deg, dec_deg, local_time, lat_deg, lon_deg, utc_offset):
    t = local_time  # (year, month, day, weekday, hour, minutes, second, n/n)
    # Zeit → UTC
    hour_local = time_to_decimal(t[4], t[5], t[6])
    hour_utc = hour_local - utc_offset
    # print("hour_utc:", hour_utc)

    # Sternzeit
    gmst = gmst_simple(t[0], t[1], t[2], hour_utc)
    lst = (gmst + lon_deg) % 360
    # print("gmst:", gmst)

    # Stundenwinkel
    ha = (lst - ra_deg) % 360
    return (gmst, equatorial_to_horizontal(ha, dec_deg, lat_deg))


def equatorial_to_horizontal(ha, dec_deg, lat_deg):
    # In Radiant
    ha_r = math.radians(ha)
    dec_r = math.radians(dec_deg)
    lat_r = math.radians(lat_deg)

    # Höhe
    sin_alt = math.sin(dec_r) * math.sin(lat_r) + math.cos(dec_r) * math.cos(
        lat_r
    ) * math.cos(ha_r)
    alt = math.asin(sin_alt)

    # Azimut
    cos_az = (math.sin(dec_r) - math.sin(alt) * math.sin(lat_r)) / (
        math.cos(alt) * math.cos(lat_r)
    )

    # numerische Stabilität
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


class timeloc:

    def __init__(self, utc_offset=2, latitude=49.68, longitude=8.62):
        self.utc_offset = utc_offset  # 2: Sommerzeit, 1: Winterzeit
        # Standort Koordinaten
        self.latitude = latitude
        self.longitude = longitude

        self.target_az = 0
        self.target_alt = 0
        self.current_az = 0
        self.current_alt = 0
        self.current_gmst = 0
        self.current_ra_deg = 0
        self.current_dec_deg = 0
        self.current_ra = ""
        self.current_dec = ""

        self.tracking_active = False
        self.movement_active = False
        self.is_calibrated = False
        self.stop_movement = False

        self.cont_mv = False
        self.cont_mv_step = False
        self.cont_mv_dir = ""
        self.cont_mv_speed = 200

    def get_localtime(self):
        # t = time.time() + UTC_OFFSET * 3600
        # (2026, 4, 9, 3, 22, 8, 36, 0)
        # (year, month, day, weekday, hour, minutes, second, n/n)
        return RTC().datetime()  # time.localtime(t)

    def update_rtc(self, year, month, day, hour, min, sec):
        RTC().datetime(
            (
                year,
                month,
                day,
                0,
                hour,
                min,
                sec,
                0,
            )
        )
        log.debug(f"year: {year}")
        log.debug(f"month: {month}")
        log.debug(f"day: {day}")
        log.debug(f"hour: {hour}")
        log.debug(f"min: {min}")
        log.debug(f"sec: {sec}")
        log.info(f"RTC gesetzt: {RTC().datetime()}")

    def set_utc_offset(self, offset):
        pass

    def set_loc(self, latitude, longitude):
        pass

    def ra_dec_to_alt_az(self, ra: str, dec: str):
        # input RA/DEC as # "06:45:07",# "-16:43:42",
        ra_deg = ra_to_deg(ra)
        dec_deg = dec_to_deg(dec)

        gmst, (alt, az) = radec_to_altaz(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            local_time=self.get_localtime(),
            lat_deg=self.latitude,
            lon_deg=self.longitude,
            utc_offset=self.utc_offset,
        )

        self.current_ra = ra
        self.current_dec = dec
        self.current_ra_deg = ra_deg
        self.current_dec_deg = dec_deg
        self.target_az = az
        self.target_alt = alt
        self.current_gmst = gmst
        return alt, az

    def set_calibration_point(self):
        log.info("Calibration point is set")
        self.current_alt = self.target_alt
        self.current_az = self.target_az
        self.is_calibrated = True

    def start_tracking(self):
        self.tracking_active = True
        self.stop_movement = False
        # TODO: Thread loop?
        # start threading for motor movement

        self.movement_routine = _thread.start_new_thread(self.tracking_loop, ())

    def stop_tracking(self):
        self.stop_movement = True
        log.debug("Wait until movement is stopped")
        while self.movement_active:
            pass
        self.tracking_active = False

    def start_cont_mv(self, dir: str):
        # dir: "n","e","w","s"
        self.cont_mv_dir = dir
        self.stop_movement = False
        self.movement_routine = _thread.start_new_thread(
            self.continuous_movement_loop, ()
        )

    def continuous_movement_loop(self):
        self.movement_active = True
        self.cont_mv = True
        while not self.stop_movement:
            self.movement_step()
        self.cont_mv = False
        self.movement_active = False
        log.info(f"Alt: {self.current_alt}, Az: {self.current_az}")

    def movement_step(self, dir=None):
        # dir: "n","e","w","s"
        if dir:
            self.cont_mv_dir = dir

        delta_deg = 0.1  # 0.25
        delay_us = stepper.slew_rate_to_us(self.cont_mv_speed)

        if self.cont_mv_dir == "n":
            # alt+
            self.target_alt = self.current_alt + delta_deg
            stepper.move_alt(delta_deg, delay_us)
            pass
        elif self.cont_mv_dir == "e":
            # az-
            self.target_az = self.current_az - delta_deg
            stepper.move_az(-delta_deg, delay_us)
            pass
        elif self.cont_mv_dir == "w":
            # az+
            self.target_az = self.current_az + delta_deg
            stepper.move_az(+delta_deg, delay_us)
            pass
        elif self.cont_mv_dir == "s":
            # alt-
            self.target_alt = self.current_alt - delta_deg
            stepper.move_alt(-delta_deg, delay_us)
            pass

        self.current_alt = self.target_alt
        self.current_az = self.target_az
        log.info(f"Alt: {self.current_alt}, Az: {self.current_az}")

    def tracking_loop(self):
        log.info(
            f"Tracking is started at Alt: {self.current_alt}, Az: {self.current_az}"
        )
        self.movement_active = True
        rest1 = 0.0
        rest2 = 0.0

        while not self.stop_movement:
            time.sleep(1)
            # nächste Sekunde
            self.current_gmst = (self.current_gmst + GMST_PER_SEC) % 360

            lst = (self.current_gmst + 8.62) % 360
            ha = (lst - self.current_ra_deg) % 360
            self.target_alt, self.target_az = equatorial_to_horizontal(
                ha, self.current_dec_deg, self.latitude
            )

            step_alt = angle_diff(self.target_alt, self.current_alt)  # + rest1
            step_az = angle_diff(self.target_az, self.current_az)  # + rest2
            rest1, rest2 = stepper.move_alt_az(
                step_alt, step_az, rest_steps=(rest1, rest2)
            )

            self.current_alt = self.target_alt
            self.current_az = self.target_az
        log.info(
            f"Tracking is stopped at Alt: {self.current_alt}, Az: {self.current_az}"
        )
        self.tracking_active = False
        self.movement_active = False

    def run_goto(self):
        log.info(f"GoTo is started at Alt: {self.current_alt}, Az: {self.current_az}")
        log.info(f"GoTo is going to Alt: {self.target_alt}, Az: {self.target_az}")
        self.movement_active = True
        self.stop_movement = False
        step_alt = angle_diff(self.target_alt, self.current_alt)
        step_az = angle_diff(self.target_az, self.current_az)
        log.debug(f"Steps to move: Alt: {step_alt}, Az: {step_az}")
        stepper.move_alt_az(step_alt, step_az)
        self.current_alt = self.target_alt
        self.current_az = self.target_az
        log.info(f"GoTo is finished at Alt: {self.current_alt}, Az: {self.current_az}")
        self.movement_active = False


if __name__ == "__main__":
    tl = timeloc()
    print(tl.get_localtime())
    # print("alt, az:", tl.ra_dec_to_alt_az(101.2792, -16.72))
