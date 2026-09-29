# Weather, Wherever

A small Flask app for looking up current conditions and a five-day forecast by city. Weather and geocoding data are provided by [Open-Meteo](https://open-meteo.com/); no API key is needed.

## Run locally

Requires Python 3.9 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000> in your browser. Search for a city and choose Celsius or Fahrenheit.

## Tests

The tests use Python's standard library and mock provider calls, so they do not need network access:

```sh
python -m unittest discover -s tests -v
```
