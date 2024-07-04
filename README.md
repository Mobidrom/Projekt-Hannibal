# Hannibal

![test badge](https://github.com/Mobidrom/Projekt-Hannibal/actions/workflows/tests.yml/badge.svg)

Dieses Projekt hat zum Ziel die Beschränkungen und Vorrangruten für Schwerlastverkehre, welche vom [SEVAS-Projekt](https://sevas.nrw.de/) für NRW bereitgestellt werden so aufzubereiten, dass sie für das Routing mit OSM basierten Routing-Engines verwendet werden können. Die so aufbereiteten Daten werden in einer Instanz der [Valhalla Routing Engine](https://github.com/valhalla/valhalla/) und der [Valhalla Web App](https://github.com/gis-ops/valhalla-app) verwendet werden, um LKW-Routen planen sowie die Auswirkungen von Beschränkungen simulieren zu können.

Der Projektname verweist auf den karthagischen Feldherr Hannibal, der mit Elefanten die Alpen überquerte und auch Rücksicht auf Beschränkungen nehmen und die beste Route für seinen "Schwelastverkehr" finden musste.

<p align="center">
<img src="https://github.com/Mobidrom/Projekt-Hannibal/assets/30908795/3e0e05fd-9ec0-403f-8a03-a6af84364d4d" width="500"/>
</p>

### Installation

Benötigt werden:

- Python >= 3.10
- Poetry
- Osmium Tool um OSM Dateien zusammenzuführen

```bash
git clone git@github.com:Mobidrom/Projekt-Hannibal.git
cd Projekt-Hannibal
python -m venv --prompt hannibal .venv
source .venv/bin/activate
poetry install
```

Poetry installiert folgende Aliasse in der Shell:

- sevas_utils: kann verwendet werden um SEVAS Daten herunterzuladen, zu inspizieren, und zu konvertieren
- hannibal: der zentrale Entrypoint zum Orchestrieren komplexer Konversionen (mehr folgt)

### Nutzung

Von Bedeutung ist gerade erst einmal das `sevas_utils` executable mit den commands `download` und `convert`:

```
❯ sevas_utils download --help

 Usage: sevas_utils download [OPTIONS] DATA_DIR [BASE_URL]

 Lädt alle SEVAS Datensätze herunter.

╭─ Arguments ──────────────────────────────────────────────────────────╮
│ *    data_dir      PATH        [default: None] [required]            │
│      base_url      [BASE_URL]  [default:                             │
│                                https://sevas.nrw.de/osm/sevas]       │
╰──────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                          │
╰──────────────────────────────────────────────────────────────────────╯
```

```
❯ sevas_utils convert --help

 Usage: sevas_utils convert [OPTIONS] DATA_DIR OSM_IN OSM_OUT
                            [BASE_URL]

 Konvertierung von SEVAS zu OSM.

╭─ Arguments ──────────────────────────────────────────────────────────╮
│ *    data_dir      PATH        Das Directory, in dem sich die SEVAS  │
│                                Daten befinden                        │
│                                [default: None]                       │
│                                [required]                            │
│ *    osm_in        PATH        Der Pfad zur OSM Datei, die als       │
│                                Grundlage zur Konvertierung dient     │
│                                [default: None]                       │
│                                [required]                            │
│ *    osm_out       PATH        Der Pfad inkl. Dateiname, an dem die  │
│                                resultierende OSM Datei abgelegt wird │
│                                [default: None]                       │
│                                [required]                            │
│      base_url      [BASE_URL]  Die Basis URL des SEVAS Web Feature   │
│                                Service                               │
│                                [default:                             │
│                                https://sevas.nrw.de/osm/sevas]       │
╰──────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                          │
╰──────────────────────────────────────────────────────────────────────╯

```

Eine Konvertierung für NRW könnte daher etwa so aussehen:

```bash
mkdir sevas_data
sevas_utils download sevas_data
wget http://download.geofabrik.de/europe/germany/nordrhein-westfalen-latest.osm.pbf -O sevas_data/nrw.pbf
sevas_utils convert sevas_data sevas_data/nrw.pbf sevas_data/nrw_sevas.pbf
```

### Tests

Getestet wird mit `pytest`, das Starten der Test Suite könnte nicht einfacher sein:

```
source .venv/bin/activate
pytest
```

#### Testdaten

Für das Testen der SEVAS Pipeline werden sowohl SEVAS- als auch OSM-Testdaten erzeugt.
Dies geschieht unter anderem mithilfe von kleinen ASCII-"Karten" (inspiriert durch
[Valhalla's Integration Test Framework](https://github.com/valhalla/valhalla/blob/master/test/gurka/README.md)) im Modul `

Foto von © José Luiz Bernardes Ribeiro, CC BY-SA 4.0  
https://commons.wikimedia.org/w/index.php?curid=53809379
