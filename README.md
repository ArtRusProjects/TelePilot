# TelePilot

Ein MicroPython-basiertes LX200-kompatibles Steuerungsprojekt für eine RPi Pico W Montierung.

## Übersicht

TelePilot richtet auf einem Raspberry Pi Pico W einen eigenen WLAN-Access-Point ein und bietet einen einfachen LX200-kompatiblen Server auf Port `4030`.
Das System kann astronomische RA/DEC-Ziele empfangen, diese in Alt/Az umrechnen und die entsprechenden Steppermotoren ansteuern.

## Projektstruktur

- `main.py`
  - Startet den WLAN-Access-Point
  - Öffnet einen LX200-kompatiblen TCP-Server
  - Behandelt LX200-Befehle für Positions- und Zeiteinstellungen
  - Enthält Stub-Funktionen für die Motoransteuerung

- `timeloc.py`
  - Rechnet RA/DEC in Alt/Az um
  - Enthält GMST- und Horzontal-Koordinatenberechnungen
  - Verwaltung von Standort, Zeit und Tracking-Zustand

- `lx200_parser.py`
  - Parsen und Formatieren von LX200-Zeit-, Datum- und Standortangaben

- `stepper.py`
  - Schrittberechnung und einfache Steuerung für zwei Steppermotoren
  - Unterstützt separate Bewegungen für Alt- und Az-Achse

- `wifi_ap.py`
  - Richtet einen WLAN Access Point ein
  - Standard SSID: `TelePico_SkyWatcher`
  - Standard Passwort: `123456789`

- `logging.py`
  - Minimaler Logging-Wrapper für MicroPython
  - Unterstützt Konsole und Datei-Ausgabe

## Voraussetzungen

- Raspberry Pi Pico W mit MicroPython
- MicroPython-Umgebung mit Netzwerk-Unterstützung
- Zwei Steppermotoren und passende Treiber für Alt- und Az-Achse
- Passende Verdrahtung der GPIO-Pins:
  - Alt-Step: Pin 17, Dir: Pin 16
  - Az-Step: Pin 19, Dir: Pin 18

## Installation

1. MicroPython auf den Pico W laden.
2. Die Dateien aus diesem Repository auf das Gerät kopieren:
   - `main.py`
   - `timeloc.py`
   - `lx200_parser.py`
   - `stepper.py`
   - `wifi_ap.py`
   - `logging.py`
3. `main.py` als Startskript ausführen.

## Nutzung

1. Verbinde dich mit dem WLAN:
   - SSID: `TelePico_SkyWatcher`
   - Passwort: `123456789`
2. Öffne eine TCP-Verbindung zu `192.168.4.1:4030`.
3. Sende LX200-kompatible Befehle.

Beispielbefehle:

- `#GR#` - RA abrufen
- `#GD#` - DEC abrufen
- `#GVP#` - Gerätename abrufen
- `#GVN#` - Firmware-Version abrufen
- `#GC#` - Datum abrufen
- `#GL#` - Uhrzeit abrufen
- `#GG#` - Zeitzone abrufen
- `#GW#` - Tracking-Modus abrufen
- `:SrHH:MM:SS#` - Ziel-RA setzen
- `:Sd±DD:MM:SS#` - Ziel-DEC setzen
- `:SG±TT.T#` - Zeitzone setzen
- `:SLHH:MM:SS#` - Uhrzeit setzen
- `:SCMM/DD/YY#` - Datum setzen
- `:St±DD*MM#` - Breitengrad setzen

## Status und TODOs

- Die Motorsteuerung im `main.py` ist aktuell als Platzhalter implementiert.
- `timeloc.set_utc_offset()` und `timeloc.set_loc()` sind derzeit noch nicht umgesetzt.
- `goto_alt_az()` muss für die tatsächliche Ansteuerung der Stepper ergänzt werden.
- Die meisten Teile sind als Prototyp und als Grundlage für weitere Erweiterungen gedacht.

## Hinweise

- Das Projekt wurde für Entwicklung und Experimentieren ausgelegt.
- Achte beim Betrieb auf korrekte Spannungsversorgung und Motoranschlüsse.
- Die aktuelle Implementierung benutzt feste Koordinaten und Zeitfunktionen von der RTC.

## Lizenz

Kein Lizenzhinweis enthalten. Bitte bei Bedarf hinzufügen.
