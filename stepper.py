"""Stepper-Konfiguration für die Alt-/Az-Montierung.

Die Funktionen arbeiten mit relativen Winkeländerungen. Ein Aufruf von
move_alt_az(alt_delta, az_delta) bewegt die Motoren um die angegebenen
Winkel in Grad.
"""

from machine import Pin
import utime

from logging import Logger

log = Logger("Stepper")

# --- Einstellungen ---
# Schritte pro Motor-Umdrehung (abhängig von Schrittauflösung / Microstepping)
STEPS_PER_REV = 400  # 200.0  # anpassen wenn Microstepping genutzt wird

# Übersetzungsverhältnisse für Alt- und Az-Achse
GEAR_RATIO_ALT = 287.5  # 575.0  # 1:50 + 40:230
GEAR_RATIO_AZ = 53 * 2  # 53.1  # 10:531 + Microstepping

# --- Motor 1: Altitude ---
step1 = Pin(17, Pin.OUT)
dir1 = Pin(16, Pin.OUT)

# --- Motor 2: Azimut ---
step2 = Pin(19, Pin.OUT)
dir2 = Pin(18, Pin.OUT)


# --- Funktion: Winkel in Schritte ---
def angle_to_steps(angle: float) -> float:
    return (angle / 360.0) * STEPS_PER_REV


def slew_rate_to_us(slew_rate: int) -> int:
    delay_us: int = 1000
    if slew_rate == 1:
        delay_us = 3500
    elif slew_rate == 2:
        delay_us = 2000
    elif slew_rate == 3:
        delay_us = 1000
    elif slew_rate == 4:
        delay_us = 600
    else:
        log.warning(
            f"Unknown slew rate {slew_rate}, using default delay of {delay_us}us"
        )

    return delay_us


# --- Funktion: beide Motoren gleichzeitig bewegen ---
def move_alt_az(
    alt_angle: float,
    az_angle: float,
    delay_us=800,
    rest_steps: tuple[float, float] = (0.0, 0.0),
) -> tuple[float, float]:  # 2.5):
    log.debug(f"Move Motors to {alt_angle} and {az_angle}")
    alt_angle = round(alt_angle, 4)
    az_angle = round(az_angle, 4)
    log.debug(f"RoundMove Motors to {alt_angle} and {az_angle}")

    steps1 = angle_to_steps(alt_angle) * GEAR_RATIO_ALT + rest_steps[0]
    steps2 = angle_to_steps(az_angle) * GEAR_RATIO_AZ + rest_steps[1]
    log.debug(f"Steps Alt: {steps1}; Az: {steps2}")
    log.debug(f"Remaining steps Alt: {rest_steps[0]}; Az: {rest_steps[1]}")

    # Richtung setzen
    dir1.value(1 if steps1 < 0 else 0)
    dir2.value(1 if steps2 < 0 else 0)

    rest_step1 = steps1 - int(steps1)
    rest_step2 = steps2 - int(steps2)
    log.debug(f"Rest steps Alt: {rest_step1}; Az: {rest_step2}")

    steps1 = abs(int(steps1))
    steps2 = abs(int(steps2))

    max_steps = max(steps1, steps2)

    log.debug(f"Move max_steps {max_steps}")

    for i in range(max_steps):
        if i < steps1:
            step1.value(1)
        if i < steps2:
            step2.value(1)

        # time.sleep(delay_ms / 1000)
        utime.sleep_us(delay_us)

        step1.value(0)
        step2.value(0)

        # time.sleep(delay_ms / 1000)
        utime.sleep_us(delay_us)

    log.debug(f"Move Motors done")
    return rest_step1, rest_step2


def move_alt(alt_angle: float, delay_us=1000):

    steps1 = angle_to_steps(alt_angle) * GEAR_RATIO_ALT

    # Richtung setzen
    dir1.value(1 if steps1 < 0 else 0)

    rest1 = steps1 % 1

    steps1 = abs(int(steps1))

    for i in range(steps1):
        step1.value(1)

        utime.sleep_us(delay_us)

        step1.value(0)

        utime.sleep_us(delay_us)


def move_az(az_angle: float, delay_us=2000):
    steps2 = angle_to_steps(az_angle) * GEAR_RATIO_AZ

    # Richtung setzen
    dir2.value(1 if steps2 < 0 else 0)

    rest2 = steps2 % 1

    steps2 = abs(int(steps2))

    for i in range(steps2):
        step2.value(1)

        utime.sleep_us(delay_us)

        step2.value(0)

        utime.sleep_us(delay_us)


# --- Beispielaufruf ---
# move_motors(90, 180)
