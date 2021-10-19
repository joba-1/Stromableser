# Stromableser

liest Stromverbrauch vom alten ENBW Zähler per ESP32-Cam.

## Infos
* ESP32-Cam läuft mit Standard Tasmota ESP-CAM Firmware
* ESP CAM LED wird über MQTT für den Snapshot an- und ausgeschaltet.
* Bild wird über HTTP als Snapshot geladen
* Tasmota muss einmalig initialisiert werden: 
    * WCResolution 10 (1024x800 einmalig, hörer sollte auch gehen)
    * WCInit (am Besten automatisch als Rule beim Startup)
* Kamera so positionieren, dass LED Reflektionen minimiert werden
    * bei mir unten rechts mit ca. 4cm Abstand
    * siehe FreeCAD Konstruktion mit STL (hält mit Magnet)
* Bild wird mit OpenCV (Python) analysiert
* Zählerstand wird an Influx Datenbank power übermittelt
    * Datenbank power muss vorher angelegt werden
* Auswertung dann z.B. mit Grafana
* Conda Environment ocv-cam mit diesen Python-Paketen erstellen
    * jupyterlab
    * matplotlib
    * numpy
    * opencv
    * paho-mqtt
    * python
    * urllib

![boxes](https://user-images.githubusercontent.com/32450554/137973442-e5cee27e-5d02-4737-8b47-528c8889a7fb.jpg)

Starten z.B. in einer screen session
    conda activate ocv-cam
    python Stromableser.py

Influx und MQTT auf localhost (oder Code anpassen...)

Viel Spaß!
