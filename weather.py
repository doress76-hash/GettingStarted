from datetime import date

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 10


class WeatherError(Exception):
    """Raised when a weather provider request fails or returns invalid data."""


CONDITIONS = {
    0: ("Clear sky", "sun"),
    1: ("Mainly clear", "partly-cloudy"),
    2: ("Partly cloudy", "partly-cloudy"),
    3: ("Overcast", "cloud"),
    45: ("Fog", "fog"),
    48: ("Rime fog", "fog"),
    51: ("Light drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Heavy drizzle", "rain"),
    56: ("Freezing drizzle", "snow"),
    57: ("Heavy freezing drizzle", "snow"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "snow"),
    67: ("Heavy freezing rain", "snow"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Rain showers", "rain"),
    81: ("Heavy rain showers", "rain"),
    82: ("Violent rain showers", "rain"),
    85: ("Snow showers", "snow"),
    86: ("Heavy snow showers", "snow"),
    95: ("Thunderstorm", "storm"),
    96: ("Thunderstorm with hail", "storm"),
    99: ("Heavy thunderstorm with hail", "storm"),
}


def _request_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise WeatherError("Weather provider request failed.") from error
    if not isinstance(payload, dict):
        raise WeatherError("Weather provider returned an invalid response.")
    return payload


def _condition(code, is_day=True):
    if code == 0 and not is_day:
        return "Clear sky", "moon"
    return CONDITIONS.get(code, ("Conditions unavailable", "cloud"))


def _location_name(place):
    parts = [place.get("name"), place.get("admin1"), place.get("country")]
    return ", ".join(dict.fromkeys(part for part in parts if part))


def get_weather(city, unit="celsius"):
    """Return normalized weather for a city, or None when it isn't found."""
    if unit not in ("celsius", "fahrenheit"):
        raise ValueError("unit must be celsius or fahrenheit")

    geocoding = _request_json(
        GEOCODING_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    places = geocoding.get("results") or []
    if not places:
        return None
    place = places[0]

    forecast = _request_json(
        FORECAST_URL,
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "forecast_days": 5,
            "timezone": "auto",
            "temperature_unit": unit,
            "wind_speed_unit": "kmh" if unit == "celsius" else "mph",
        },
    )

    try:
        current = forecast["current"]
        current_code = int(current["weather_code"])
        current_condition, current_icon = _condition(
            current_code, is_day=bool(current.get("is_day", 1))
        )
        daily = forecast["daily"]
        days = daily["time"]
        highs = daily["temperature_2m_max"]
        lows = daily["temperature_2m_min"]
        codes = daily["weather_code"]
        if not days or not (len(days) == len(highs) == len(lows) == len(codes)):
            raise ValueError("Forecast day fields do not match.")

        forecast_days = []
        for day, high, low, code in zip(days, highs, lows, codes):
            forecast_date = date.fromisoformat(day)
            condition, icon = _condition(int(code))
            forecast_days.append(
                {
                    "weekday": forecast_date.strftime("%A"),
                    "date": forecast_date.strftime("%b %d").replace(" 0", " "),
                    "high": high,
                    "low": low,
                    "condition": condition,
                    "icon": icon,
                }
            )
    except (KeyError, TypeError, ValueError) as error:
        raise WeatherError("Weather provider returned incomplete data.") from error

    return {
        "location": _location_name(place),
        "unit_symbol": "°C" if unit == "celsius" else "°F",
        "wind_unit": forecast.get("current_units", {}).get("wind_speed_10m", "km/h"),
        "current": {
            "temperature": current["temperature_2m"],
            "feels_like": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "wind_speed": current["wind_speed_10m"],
            "condition": current_condition,
            "icon": current_icon,
        },
        "forecast": forecast_days,
    }
