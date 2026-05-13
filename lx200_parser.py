import math


def parse_date(date_str):
    # "04/02/26"
    m, d, y = map(int, date_str.split("/"))
    y += 2000  # 2-digit year
    return y, m, d


def parse_time(time_str):
    # "12:34:56"
    h, m, s = map(int, time_str.split(":"))
    return h, m, s


def format_lat(deg):
    # deg = math.degrees(lat_rad)

    sign = "+" if deg >= 0 else "-"

    deg = abs(deg)

    d = int(deg)
    m = int((deg - d) * 60)

    return "%s%02d*%02d#" % (sign, d, m)


def format_lon(deg):
    deg = -deg  # math.degrees(lon_rad)

    sign = "+" if deg >= 0 else "-"

    deg = abs(deg)

    d = int(deg)
    m = int((deg - d) * 60)

    return "%s%03d*%02d#" % (sign, d, m)


def parse_lat(lat_str):
    # +48*08
    sign = 1

    if lat_str[0] == "-":
        sign = -1

    lat_str = lat_str[1:]

    deg, minute = lat_str.split("*")

    val = sign * (float(deg) + float(minute) / 60)

    return val  # math.radians(val)


def parse_lon(lon_str):
    # Beispiel:
    # 351*36

    deg, minute = lon_str.split("*")

    val = float(deg) + float(minute) / 60

    # 0..360 → -180..180
    if val > 180:
        val -= 360

    # Jetzt:
    # 351°36 → -8°24

    # Invertieren!
    val = -val

    return val  # math.radians(val)
