import network
import time
import machine
from logging import Logger

log = Logger("Wifi_AP")


def setup_access_point(ssid: str, pw: str):
    # network.WLAN.disconnect(network.AP_IF)
    # machine.reset()
    # time.sleep(5)

    ap = network.WLAN(network.AP_IF)
    # ap.active(False)
    time.sleep(1)

    ap.config(essid=ssid, password=pw)
    ap.active(True)

    log.info(f"AP gestartet: {ap.ifconfig()[0]}")
    # log.info(f"Current time (UTC): {RTC().datetime()}")


if __name__ == "__main__":
    ssid = "Test"
    pw = "test1"
    setup_access_point(ssid, pw)
