Dieses Projekt hat zum Ziel die Beschränkungen und Vorrangruten für Schwerlastverkehre, welche vom [SEVAS-Projekt](https://sevas.nrw.de/) für NRW bereitgestellt werden so aufzubereiten, dass sie für das Routing mit OSM basierten Routing-Engines verwendet werden können. Die so aufbereiteten Daten werden in einer Instanz der [Valhalla Routing Engine](https://github.com/valhalla/valhalla/) und der [Valhalla Web App](https://github.com/gis-ops/valhalla-app) verwendet werden, um LKW-Routen planen sowie die Auswirkungen von Beschränkungen simulieren zu können.

Der Projektname verweist auf den karthagischen Feldherr Hannibal, der mit Elefanten die Alpen überquerte und auch Rücksicht auf Beschränkungen nehmen und die beste Route für seinen "Schwelastverkehr" finden musste.
<img src="https://github.com/Mobidrom/Projekt-Hannibal/assets/30908795/3e0e05fd-9ec0-403f-8a03-a6af84364d4d" width="500"/>

### Installation

Benötigt werden:

- Python >= 3.9
- Poetry

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

### Tests

Getestet wird mit `pytest`, das Starten der Test Suite könnte nicht einfacher sein:

```
source .venv/bin/activate
pytest
```

Foto von © José Luiz Bernardes Ribeiro, CC BY-SA 4.0  
https://commons.wikimedia.org/w/index.php?curid=53809379
