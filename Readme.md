# Stromableser

liest Stromverbrauch vom alten ENBW Zähler per ESP32-Cam.

![boxes](https://user-images.githubusercontent.com/32450554/137973442-e5cee27e-5d02-4737-8b47-528c8889a7fb.jpg)

## Infos
* ESP32-Cam läuft mit Standard Tasmota ESP-CAM Firmware
* ESP CAM LED wird über MQTT für den Snapshot an- und ausgeschaltet.
* Bild wird über HTTP als Snapshot geladen
* Tasmota muss einmalig initialisiert werden: 
    * WCResolution 10 (1024x800 einmalig, hörer sollte auch gehen)
    * WCInit (am Besten automatisch als Rule beim Startup)
    * Dimmer 90 (Helligkeit ggf. für gutes Bild anpassen)
    * PowerOnState 0 (LED erst mal aus. Kann sonst heiß werden)
* Kamera so positionieren, dass LED Reflektionen minimiert werden
    * bei mir unten rechts mit ca. 4cm Abstand
    * siehe FreeCAD Konstruktion mit STL (hält mit Magnet)
* Bild wird mit OpenCV (Python) analysiert (ggf. anpassen)
    * Größte Box-Kontour im Bild wird zum gerade richten verwendet
    * Code geht von 6-Digits rechts in der Box-Kontur und etwas abgesetzter Kommastelle rechts von der Box aus
    * Ziffern-Vorlagen sind in digits.npz (ggf. anpassen -> siehe Stromableser.ipynb)
* Zählerstand wird an Influx Datenbank power übermittelt
    * Datenbank power muss vorher angelegt werden
    * ```influx> create database power```
* Auswertung dann z.B. mit Grafana
    * ```SELECT non_negative_difference(mean("watt")) FROM "energy" WHERE ("meter" = 'main') AND $timeFilter GROUP BY time($__interval) fill(null)```
* Conda Environment ocv-cam mit diesen Python-Paketen erstellen
    * jupyterlab
    * matplotlib
    * numpy
    * opencv
    * paho-mqtt
    * python
    * urllib

Starten
* manuell in einer screen session
    ```
    conda activate ocv-cam
    python Stromableser.py
    ```
* automatisch mit dem Skript und dem Service (ggf. im Service den User anpassen) 
    ```
    conda init
    sudo mkdir -p /var/log/ocv-cam /usr/local/ocv-cam
    sudo chown $USER /var/log/ocv-cam /usr/local/ocv-cam
    cp -a Stromableser.sh /usr/local/ocv-cam/
    sudo cp -a Stromableser.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl start Stromableser
    ```
Influx und MQTT auf localhost (oder Code anpassen...)

Viel Spaß!
