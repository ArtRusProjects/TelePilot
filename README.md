# TelePilot

Ein MicroPython-basiertes LX200-kompatibles Steuerungsprojekt für eine RPi Pico W Montierung.

## Übersicht

TelePilot richtet auf einem Raspberry Pi Pico W einen eigenen WLAN-Access-Point ein und bietet einen einfachen LX200-kompatiblen Server auf Port `4030`.
Das System kann astronomische RA/DEC-Ziele empfangen, diese in Alt/Az umrechnen und die entsprechenden Steppermotoren ansteuern.

## Projektstruktur

- `main.py`
  - Startet den WLAN-Access-Point
  - Öffnet einen LX200-kompatiblen TCP-Server
  - Verarbeitet LX200-Befehle über eine zentrale Parser-Schicht
  - Nutzt `stepper.py` für Motorbewegungen

- `timeloc.py`
  - Rechnet RA/DEC in Alt/Az um
  - Enthält GMST- und Horizontalkoordinatenberechnungen
  - Verwaltung von Standort, Zeit, Zeitzone und Tracking-Zustand

- `lx200_parser.py`
  - Zentralisiert die LX200-Kommandoverarbeitung
  - Formatiert Datum, Uhrzeit, Breitengrad und Längengrad
  - Nutzt den `timeloc`-Zustand für Antworten und Befehle

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
- Kalibrierungs-Taster an Pin 20 (verbunden zu GND bei Betätigung)
- Passende Verdrahtung der GPIO-Pins:
  - Alt-Step: Pin 17, Dir: Pin 16
  - Az-Step: Pin 19, Dir: Pin 18
  - Kalibrierungs-Taster: Pin 20 → GND

## Installation

1. Installiere MicroPython auf dem Raspberry Pi Pico W.
2. Öffne die MicroPython-Shell oder das Dateimanager-Tool deiner Wahl.
3. Kopiere die Dateien aus diesem Repository auf den Pico W:
   - `main.py`
   - `timeloc.py`
   - `lx200_parser.py`
   - `stepper.py`
   - `wifi_ap.py`
   - `logging.py`
4. Setze `main.py` als Startskript, damit es beim Booten ausgeführt wird.

### Native Alt/Az-Berechnung

Die Berechnung von GMST, Präzession und Alt/Az liegt im nativen MicroPython-
C-Modul unter `cmodules/altaz`. Für eine eigene Pico-Firmware muss der
MicroPython-Build dieses Verzeichnis als `USER_C_MODULES` einbinden:

```bash
make -C ports/rp2 submodules
make -C ports/rp2 BOARD=RPI_PICO_W \
  USER_C_MODULES=/path/to/TelePilot/cmodules/altaz/micropython.cmake
```

Danach stellt die Firmware `import altaz` und `altaz.calculate(...)` bereit.
`dev_ctrl.py` verwendet dann automatisch den C-Pfad; ohne native Firmware
bleibt die Python-Berechnung für Host-Tests als Fallback verfügbar.

## Erste Schritte

1. Starte den Pico W und warte, bis der Access Point aktiv ist.
2. Verbinde dein Gerät mit dem WLAN:
   - SSID: `TelePico_SkyWatcher`
   - Passwort: `123456789`
3. Öffne eine TCP-Verbindung zur IP `192.168.4.1` auf Port `4030`.
4. Sende LX200-kompatible Befehle.

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
- `:CM#` - Kalibrierungspunkt setzen / 2-Stern-Kalibrierung

## 2-Stern-Kalibrierung

Das Projekt unterstützt jetzt einen einfachen 2-Stern-Kalibrierungsablauf über das LX200-Kommando `:CM#`.

### Hardwarevoraussetzung
- Kalibrierungs-Taster an Pin 20 angeschlossen (zu GND bei Betätigung)
- Der Taster wird über PULL_UP gelesen (gedrückt = GND = Wert 0)

### Kalibrierungsablauf

**Mit Taster gedrückt: Kalibrierungspunkt speichern**
1. Setze mit `:Sr...#` und `:Sd...#` den ersten Stern als Ziel
2. Richte die Montierung manuell auf den ersten Stern aus
3. **Halte den Taster an Pin 20 gedrückt** und sende `:CM#`
   - Kalibrierungspunkt wird gespeichert
   - Tracking startet
4. Wiederhole Schritte 1-3 für einen zweiten Stern
5. Nach dem zweiten Punkt mit gedrücktem Taster: Das System berechnet die Alt/Az-Offsets automatisch

**Ohne Taster gedrückt: Nur Tracking starten**
- Sende `:CM#` ohne Taster zu drücken → Tracking startet mit bestehenden Kalibrierungspunkten
- Dies verhindert, dass die Kalibrierung durch wiederholte CM-Befehle verfälscht wird

### Ergebnis
Nach zwei Kalibrierungspunkten werden alle weiteren Zielberechnungen mit den errechneten Alt/Az-Offsets korrigiert.

## Status und TODOs

- Die LX200-Kommandos werden jetzt zentral in `lx200_parser.py` verarbeitet.
- `timeloc.set_utc_offset()` und `timeloc.set_loc()` sind implementiert.
- `main.py` kann Verbindungen dauerhaft akzeptieren und Befehle in einer Schleife verarbeiten.
- `goto_alt_az()` nutzt jetzt `stepper.move_alt_az()` für relative Bewegungen.
- `:CM#` kann jetzt zwei Kalibrierungspunkte aufnehmen (bei gedrücktem Taster an Pin 20) und einen einfachen Alt/Az-Offset berechnen.
- `:CM#` ohne Taster startet nur Tracking mit bestehenden Kalibrierungspunkten (verhindert Kalibrierungsverfälschung).
- Tracking und Kalibrierung sind weiterhin prototypisch und sollten vor dem Einsatz auf der echten Montierung getestet werden.

## Hinweise

- Das Projekt wurde für Entwicklung und Experimentieren ausgelegt.
- Achte beim Betrieb auf korrekte Spannungsversorgung und Motoranschlüsse.
- Die aktuelle Implementierung benutzt feste Koordinaten und Zeitfunktionen von der RTC.

## Lizenz

Kein Lizenzhinweis enthalten. Bitte bei Bedarf hinzufügen.
