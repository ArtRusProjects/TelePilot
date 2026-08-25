import socket
from logging import Logger
from machine import Pin

from dev_ctrl import dev_ctrl
import wifi_ap
import lx200_parser as lx200

# import stepper

log = Logger("Main")

PORT = 4030
SSID = "TelePico_SkyWatcher"
PASSWORD = "123456789"

pinLED = Pin("LED", Pin.OUT)


def extract_lx200_messages(buffer):
    messages = []

    while buffer:
        if buffer.startswith("Ka"):
            messages.append("Ka")
            buffer = buffer[2:]
            continue

        if buffer.startswith("#\x06"):
            messages.append("#\x06")
            buffer = buffer[2:]
            continue

        start = buffer.find("#")
        if start == -1:
            break

        end = buffer.find("#", start + 1)
        if end == -1:
            break

        messages.append(buffer[start : end + 1])
        buffer = buffer[end + 1 :]

    return messages, buffer


def handle_client(conn, addr, state: lx200.LX200State):
    log.info("Verbindung angenommen: %s", addr)
    buffer = ""
    not_shown_commands = ["#:GR#", "#:GW#", "#:GD#", "#:D#"]

    try:
        while True:
            pinLED.on()
            data = conn.recv(64)
            if not data:
                log.info("Verbindung geschlossen: %s", addr)
                break

            buffer += data.decode("utf-8", "ignore")
            commands, buffer = extract_lx200_messages(buffer)

            for command in commands:
                if command not in not_shown_commands:
                    log.debug("Empfangenes LX200-Kommando: %s", command)
                response = lx200.handle_command(command, state)
                if response is not None:
                    if command not in not_shown_commands:
                        log.debug("Antwort LX200: %s", response)
                    conn.send(response)

    except Exception as exc:
        log.error("Fehler in Verbindung %s: %s", addr, exc)
    finally:
        conn.close()
        pinLED.off()
        log.info("Verbindung getrennt: %s", addr)


def run_server(state: lx200.LX200State):
    server_socket = socket.socket()
    server_socket.bind(("0.0.0.0", PORT))
    server_socket.listen(1)

    log.info("LX200 Server läuft auf Port %s", PORT)

    while True:
        try:
            conn, addr = server_socket.accept()
            handle_client(conn, addr, state)
        except Exception as exc:
            log.error("Server-Fehler: %s", exc)
            # continue
        finally:
            server_socket.close()
            log.info("Server-Socket geschlossen")
            break


if __name__ == "__main__":
    wifi_ap.setup_access_point(ssid=SSID, pw=PASSWORD)

    device = dev_ctrl()
    lx200_state = lx200.LX200State(device)

    run_server(lx200_state)
