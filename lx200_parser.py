import math


def parse_date(date_str):
    """Parst LX200-Datum im Format MM/DD/YY."""
    m, d, y = map(int, date_str.split("/"))
    y += 2000  # 2-digit year
    return y, m, d


def parse_time(time_str):
    """Parst LX200-Zeit im Format HH:MM:SS."""
    h, m, s = map(int, time_str.split(":"))
    return h, m, s


def format_lat(deg):
    """Formatiert Breitengrad für LX200 (#Gt#) als +DD*MM#."""
    sign = "+" if deg >= 0 else "-"
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    return "%s%02d*%02d#" % (sign, d, m)


def format_lon(deg):
    """Formatiert Längengrad für LX200 (#Gg#) als +DDD*MM#."""
    deg = -deg
    sign = "+" if deg >= 0 else "-"
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    return "%s%03d*%02d#" % (sign, d, m)


def parse_lat(lat_str):
    """Parst LX200-Breitengrad im Format ±DD*MM."""
    sign = 1
    if lat_str[0] == "-":
        sign = -1
    lat_str = lat_str[1:]
    deg, minute = lat_str.split("*")
    val = sign * (float(deg) + float(minute) / 60)
    return val


def parse_lon(lon_str):
    """Parst LX200-Längengrad im Format DDD*MM."""
    deg, minute = lon_str.split("*")
    val = float(deg) + float(minute) / 60
    if val > 180:
        val -= 360
    return -val


def format_ra_lx200(ra_str):
    """Gibt eine RA-Zeichenkette im LX200-Format zurück."""
    return "%s#" % ra_str


def format_dec_lx200(dec_str):
    """Gibt eine DEC-Zeichenkette im LX200-Format zurück."""
    sign = "+" if dec_str.startswith("+") else "-"
    h, m, s = map(int, dec_str.replace("+", "").replace("-", "").split(":"))
    return "%s%02d*%02d:%02d#" % (sign, h, m, s)


def format_time_lx200(local_time):
    return "%02d:%02d:%02d#" % (local_time[4], local_time[5], local_time[6])


def format_date_lx200(local_time):
    return "%02d/%02d/%02d#" % (local_time[1], local_time[2], local_time[0] % 100)


def _angle_diff(a, b):
    d = a - b
    if d > 180:
        d -= 360
    if d < -180:
        d += 360
    return d


class LX200State:
    def __init__(self, timeloc):
        self.tl = timeloc
        self.ra_target = None
        self.dec_target = None
        self.pending_time = None
        self.pending_date = None
        self.time_set = False
        self.date_set = False
        self.current_ra = "05:00:00"
        self.current_dec = "+20:00:00"
        self.current_alt = 0.0
        self.current_az = 0.0


def _apply_rtc_update(state):
    if state.time_set and state.date_set:
        year, month, day = state.pending_date
        hour, minute, second = state.pending_time
        state.tl.update_rtc(year, month, day, hour, minute, second)
        state.time_set = False
        state.date_set = False


def _execute_goto(state, goto_callback):
    if state.ra_target is None or state.dec_target is None:
        return

    alt, az = state.tl.ra_dec_to_alt_az(state.ra_target, state.dec_target)
    delta_alt = _angle_diff(alt, state.current_alt)
    delta_az = _angle_diff(az, state.current_az)

    if goto_callback:
        goto_callback(delta_alt, delta_az)

    state.current_alt = alt
    state.current_az = az
    state.current_ra = state.ra_target
    state.current_dec = state.dec_target
    state.ra_target = None
    state.dec_target = None


def handle_command(command, state, goto_callback=None):
    if command == "Ka":
        return None

    if command == "##":
        return b"0#"

    if command == "#\x06":
        return b"P"

    if not command.startswith("#") or not command.endswith("#"):
        return None

    body = command[2:-1]

    if body == "GR":
        return format_ra_lx200(state.current_ra).encode()

    if body == "GD":
        return format_dec_lx200(state.current_dec).encode()

    if body == "GVP":
        return b"TelePico#"

    if body == "GVN":
        return b"1.0#"

    if body == "GVD":
        return format_date_lx200(state.tl.get_localtime()).encode()

    if body == "GVT":
        return format_time_lx200(state.tl.get_localtime()).encode()

    if body == "Gg":
        return format_lon(state.tl.longitude).encode()

    if body == "Gt":
        return format_lat(state.tl.latitude).encode()

    if body == "GC":
        return format_date_lx200(state.tl.get_localtime()).encode()

    if body == "GL":
        return format_time_lx200(state.tl.get_localtime()).encode()

    if body == "GG":
        return ("%+0.1f#" % (-state.tl.utc_offset)).encode()

    if body == "GW":
        return b"AltAz Tracking#"

    if body == "D":
        return b"#"

    if body.startswith("Sr"):
        state.ra_target = body[2:]
        return b"1"

    if body.startswith("Sd"):
        state.dec_target = body[2:]
        return b"1"

    if body.startswith("SG"):
        try:
            val = float(body[2:])
            state.tl.set_utc_offset(-val)
            return b"1"
        except Exception:
            return b"0"

    if body.startswith("SL"):
        try:
            state.pending_time = parse_time(body[2:])
            state.time_set = True
            _apply_rtc_update(state)
            return b"1"
        except Exception:
            return b"0"

    if body.startswith("SC"):
        try:
            state.pending_date = parse_date(body[2:])
            state.date_set = True
            _apply_rtc_update(state)
            return b"1Updating Planetary Data#"
        except Exception:
            return b"0"

    if body.startswith("St"):
        try:
            latitude = parse_lat(body[2:])
            state.tl.set_loc(latitude, state.tl.longitude)
            return b"1"
        except Exception:
            return b"0"

    if body.startswith("Sg"):
        try:
            longitude = parse_lon(body[2:])
            state.tl.set_loc(state.tl.latitude, longitude)
            return b"1"
        except Exception:
            return b"0"

    if body == "CM":
        # Calibration/sync: record current mount position for the current RA/DEC target.
        if state.ra_target and state.dec_target:
            state.current_ra = state.ra_target
            state.current_dec = state.dec_target

            alt, az = state.tl.ra_dec_to_alt_az(
                state.ra_target, state.dec_target, apply_calibration=False
            )

            actual_alt = state.current_alt
            actual_az = state.current_az
            if (
                not state.tl.calibration_points
                and abs(actual_alt - alt) < 1e-6
                and abs(_angle_diff(actual_az, az)) < 1e-6
            ):
                actual_alt = alt
                actual_az = az

            state.tl.add_calibration_point(
                state.ra_target, state.dec_target, actual_alt, actual_az
            )
            state.current_alt = actual_alt
            state.current_az = actual_az
            state.tl.start_tracking()
            state.ra_target = None
            state.dec_target = None
        return b"0"

    if body.startswith("Q"):
        if len(body) > 1 and body[1] != "#" and not state.tl.cont_mv:
            state.tl.cont_mv_step = True
        else:
            state.tl.stop_tracking()
        return b"0#"

    if body in ["RG", "RC", "RM", "RS"]:
        slew_rate_dict = {"G": 1, "C": 2, "M": 3, "S": 4}
        state.tl.cont_mv_speed = slew_rate_dict.get(body[1], state.tl.cont_mv_speed)
        return b"0"

    if body == "MS":
        _execute_goto(state, goto_callback)
        return b"0#"

    if body in ["Mn", "Mw", "Me", "Ms"]:
        if state.tl.cont_mv_step:
            state.tl.movement_step(dir=body[1])
            state.tl.cont_mv_step = False
        else:
            state.tl.start_cont_mv(dir=body[1])
        return b"0"

    return b"0#"
