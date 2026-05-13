import network
import socket
import time
import math
from logging import Logger
from timeloc import timeloc
import wifi_ap
import lx200_parser as lx200
from machine import RTC, Pin

log = Logger("Main")
tl = timeloc()


wifi_ap.setup_access_point(ssid="TelePico_SkyWatcher", pw="123456789")

pinLED = Pin("LED", Pin.OUT)


# =========================
# KONFIG
# =========================
PORT = 4030


pending_hour = 0
pending_min = 0
pending_sec = 0

pending_day = 1
pending_month = 1
pending_year = 2026

mv_active = False
tracing_active = False


# =========================
# HILFSFUNKTIONEN
# =========================


def get_time_lx200():
    # TODO auslagern in lx200
    t = tl.get_localtime()
    return "%02d:%02d:%02d#" % (t[4], t[5], t[6])


def get_date_lx200():
    # TODO auslagern in lx200
    t = tl.get_localtime()
    return "%02d/%02d/%02d#" % (t[1], t[2], t[0] % 100)


# =========================
# MOTOR (PLATZHALTER)
# =========================
def goto_alt_az(alt, az):
    log.debug("=== GOTO ===")
    log.debug(f"ALT: {math.degrees(alt)}")
    log.debug(f"AZ : {math.degrees(az)}")
    log.debug("============")

    # HIER: deine Stepper ansteuern!


# =========================
# LX200 SERVER
# =========================
_socket = socket.socket()
_socket.bind(("0.0.0.0", PORT))
_socket.listen(1)

log.info(f"LX200 Server läuft auf Port {PORT}")
try:
    conn, addr = _socket.accept()
    log.info(f"Verbunden: {addr}")
except Exception as e:
    log.error(e)
finally:
    _socket.close()
    log.error("fin")

ra_target = None
dec_target = None
ra_current = "05:00:00"  # Dummy RA
dec_current = "+20:00:00"  # Dummy DEC

time_set = False
date_set = False

buffer = ""

try:
    while True:
        pinLED.on()
        data = conn.recv(64)
        if not data:
            break

        buffer += data.decode()
        if buffer not in ["#:GR#", "#:GD#", "#:D#", "#:GW#"]:
            log.debug(f"Buffer: {buffer}")
        else:
            log.log(0, f"Buffer: {buffer}")

        # -------------------------
        # INITIALISATION
        # -------------------------

        if buffer.startswith("Ka"):
            # conn.send(b"#")
            log.debug("Received 'Ka' -> will skip")
            buffer = ""
            continue

        if buffer.startswith("##"):
            log.debug("Received '##' -> send back '0#'")
            conn.send(b"0#")
            buffer = ""

            continue

        if buffer == "#\x06":
            log.debug("Received '#\x06' -> send back 'P'")
            conn.send(b"P")
            buffer = ""
            continue

        res = None

        while "#:" in buffer:
            pinLED.off()
            # _, cmd, buffer = buffer.split("#")
            cmd = buffer[1:]
            # cmd += "#"

            # print("CMD:", cmd)

            # -------------------------
            # GET TELESCOPE INFORMATIONS
            # -------------------------
            if cmd == ":GR#":  # RA Format: "05:00:00"
                res = (ra_current + "#").encode()

            elif cmd == ":GD#":  # DEC Format: "+20*00:00"
                h, m, s = map(int, dec_current.split(":"))
                dec = f"{h}*{m}:{s}#"
                res = dec.encode()

            elif cmd == ":GVP#":
                res = b"TelePico#"

            elif cmd == ":GVN#":
                res = b"1.0#"

            elif cmd == ":GVD#":
                res = b"2026-01-01#"

            elif cmd == ":GVT#":
                res = b"12:00:00#"

            elif cmd == ":Gg#":
                # res = b"-008*37#"
                res = lx200.format_lon(tl.longitude).encode()

            elif cmd == ":Gt#":
                # res = b"+49*41#"
                res = lx200.format_lat(tl.latitude).encode()

            elif cmd == ":GC#":
                res = get_date_lx200().encode()  # b"04/02/26#"

            elif cmd == ":GL#":
                res = get_time_lx200().encode()  # b"21:41:59#"

            elif cmd == ":GG#":
                res = (
                    "%+0.1f#" % (tl.utc_offset * -1)  # invertiert für lx200
                ).encode()  # b"+02.0#"  # +01.0# für Winterzeit oder +02.0# für Sommerzeit

            elif cmd == ":GW#":
                res = b"AltAz Tracking#"

            elif cmd == ":D#":
                res = b"#"

            # -------------------------
            # SET TARGET
            # -------------------------
            elif cmd.startswith(":Sr"):
                # set target RA
                ra_target = cmd[3:-1]
                log.debug(f"RA is set: {ra_target}")

                res = b"1"  # OK

            elif cmd.startswith(":Sd"):
                # set target DEC
                dec_target = cmd[3:-1]
                log.debug(f"DEC is set: {dec_target}")

                res = b"1"  # OK

            elif cmd.startswith(":SG"):
                # set timezone (utc offset)
                # dec_target = cmd[3:-1]
                try:
                    val = float(cmd[3:-1])  # z.B. -2.0

                    # lx200_offset = val
                    tl.set_utc_offset(-val)  # invertiert für interne Nutzung

                    res = b"1"  # OK
                except:
                    res = b"0"  # not OK

            elif cmd.startswith(":SL"):
                # set time
                try:
                    t = cmd[3:-1]
                    h, m, s = lx200.parse_time(t)

                    pending_hour = h
                    pending_min = m
                    pending_sec = s

                    time_set = True

                    # if time_set and date_set:
                    #     update_rtc()
                    #     time_set = False
                    #     date_set = False

                    res = b"1"
                except:
                    res = b"0"

            elif cmd.startswith(":SC"):
                # set date
                try:
                    d = cmd[3:-1]
                    y, m, d = lx200.parse_date(d)

                    pending_year = y
                    pending_month = m
                    pending_day = d

                    date_set = True

                    res = b"1Updating Planetary Data#"
                except:
                    res = b"0"

            elif cmd.startswith(":St"):
                # set latitude

                try:
                    tl.latitude = lx200.parse_lat(cmd[3:-1])
                    log.debug(f"set latitude: {tl.latitude}")

                    res = b"1"
                except:
                    res = b"0"

            elif cmd.startswith(":Sg"):
                # set longitude

                try:
                    tl.longitude = lx200.parse_lon(cmd[3:-1])
                    log.debug(f"set longitude: {tl.longitude}")

                    res = b"1"
                except:
                    res = b"0"

            elif cmd.startswith(":CM"):
                # sync calibration
                # log.info("TODO: Set calibration point")
                if ra_target and dec_target:
                    tl.stop_tracking()
                    # ra = ra_to_deg(ra_target)
                    # dec = dec_to_deg(dec_target)
                    log.debug(f"RA: {ra_target}, DEC: {dec_target}")
                    alt, az = tl.ra_dec_to_alt_az(ra_target, dec_target)
                    log.debug(f"Alt: {alt}, Az: {az}")

                    ra_current = ra_target
                    dec_current = dec_target
                    ra_target = None
                    dec_target = None

                    # if not tl.is_calibrated:
                    tl.set_calibration_point()
                    tl.start_tracking()
                res = b"0"

            elif cmd.startswith(":Q"):
                # stop movement
                if cmd[2] != "#" and not tl.cont_mv:
                    tl.cont_mv_step = True
                else:
                    tl.stop_tracking()
                res = b"0#"

            elif cmd in [":RG#", ":RC#", ":RM#", ":RS#"]:
                # set slew rate 1:RG (lowest) 2:RC 3:RM 4:RS (fastest)
                slew_rate_dict = {"G": 1, "C": 2, "M": 3, "S": 4}

                tl.cont_mv_speed = slew_rate_dict[cmd[2]]
                log.debug(f"Set slew rate to {tl.cont_mv_speed}")

                # only for testing -> reset alt az
                # if tl.cont_mv_speed == 1:
                #     tl.current_alt = 0
                #     tl.current_az = 0

                res = b"0"

            # -------------------------
            # Movement
            # -------------------------
            elif cmd == ":MS#":
                # start GoTo
                log.info("Perform GoTo...")

                if ra_target and dec_target:
                    tl.stop_tracking()
                    # ra = ra_to_deg(ra_target)
                    # dec = dec_to_deg(dec_target)
                    log.debug(f"RA: {ra_target}, DEC: {dec_target}")
                    alt, az = tl.ra_dec_to_alt_az(ra_target, dec_target)
                    log.debug(f"Alt: {alt}, Az: {az}")

                    ra_current = ra_target
                    dec_current = dec_target
                    ra_target = None
                    dec_target = None

                    tl.run_goto()
                res = b"0#"
                #     res = b"0#"  # Erfolg
                # else:
                #     res = b"1#"  # Fehler

            elif cmd in [":Mn#", ":Mw#", ":Me#", ":Ms#"]:
                # move NWES directly
                if tl.cont_mv_step:
                    # move one step*
                    log.debug("One step movement")
                    tl.movement_step(dir=cmd[2])
                    tl.cont_mv_step = False
                else:
                    log.debug("Continouos movement")
                    tl.start_cont_mv(dir=cmd[2])

                res = b"0"

            else:
                res = b"0#"

            # -------------------------
            # SEND MESSAGE
            # -------------------------
            if res:
                if cmd not in [":GR#", ":GD#", ":D#", ":GW#"]:
                    log.debug(f"Send: {res}")
                else:
                    log.log(0, f"Send: {res}")

                conn.send(res)
                res = None
                buffer = ""

                if time_set and date_set:
                    tl.update_rtc(
                        pending_year,
                        pending_month,
                        pending_day,
                        pending_hour,
                        pending_min,
                        pending_sec,
                    )
                    time_set = False
                    date_set = False

                break
except Exception as e:
    log.error(e)
finally:
    tl.stop_tracking()
    _socket.close()
