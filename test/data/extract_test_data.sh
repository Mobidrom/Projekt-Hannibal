#!/usr/bin/env bash

# erstellt kleinen SEVAS Testdatensatz aus tatsächlichen 
# SEVAS Daten. Dieses Skript dient hauptsächlich der Dokumentation,
# da das wiederholte Erstellen dieses Datensatzes aus neueren Quelldaten
# bestehende Tests brechen kann 

for f in sevas_data/*.shp ; do 
    new=$(basename -s .shp $f)_koeln.shp

    echo "Clipping $f, writing to $new"
    ogr2ogr -clipdst 6.859932 50.877911 7.044296 51.011811 test/data/$new $f
done