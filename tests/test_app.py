import unittest
from unittest.mock import Mock, call, patch

import app as weather_app
import weather


class WeatherServiceTests(unittest.TestCase):
    @staticmethod
    def response(payload):
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    @patch("weather.requests.get")
    def test_get_weather_normalizes_current_and_five_day_forecast(self, get):
        get.side_effect = [
            self.response(
                {"results": [{"name": "Portland", "admin1": "Oregon", "country": "United States", "latitude": 45.52, "longitude": -122.68}]}
            ),
            self.response(
                {
                    "current": {
                        "temperature_2m": 18.4,
                        "apparent_temperature": 17.9,
                        "relative_humidity_2m": 62,
                        "wind_speed_10m": 11.2,
                        "weather_code": 2,
                        "is_day": 1,
                    },
                    "current_units": {"wind_speed_10m": "km/h"},
                    "daily": {
                        "time": ["2026-09-25", "2026-09-26"],
                        "temperature_2m_max": [20.0, 21.0],
                        "temperature_2m_min": [12.0, 13.0],
                        "weather_code": [2, 61],
                    },
                }
            ),
        ]

        result = weather.get_weather("Portland", "celsius")

        self.assertEqual(result["location"], "Portland, Oregon, United States")
        self.assertEqual(result["current"]["condition"], "Partly cloudy")
        self.assertEqual(result["forecast"][1]["condition"], "Light rain")
        self.assertEqual(result["unit_symbol"], "°C")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["temperature_unit"], "celsius")
        self.assertEqual(get.call_args_list[1].kwargs["params"]["forecast_days"], 5)

    @patch("weather.requests.get")
    def test_get_weather_returns_none_for_unknown_city(self, get):
        get.return_value = self.response({"results": None})
        self.assertIsNone(weather.get_weather("Nowhere"))
        self.assertEqual(get.call_count, 1)

    @patch("weather.requests.get")
    def test_provider_errors_are_wrapped(self, get):
        import requests

        get.side_effect = requests.Timeout("provider timed out")
        with self.assertRaises(weather.WeatherError):
            weather.get_weather("Boston")


class FlaskRouteTests(unittest.TestCase):
    def setUp(self):
        weather_app.app.config["TESTING"] = True
        self.client = weather_app.app.test_client()

    def test_home_page_shows_search(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Search a city", response.data)
        self.assertIn(b"value=\"celsius\" selected", response.data)

    @patch("app.get_weather")
    def test_search_renders_current_weather_and_forecast(self, get_weather):
        get_weather.return_value = {
            "location": "Kyoto, Kyoto, Japan",
            "unit_symbol": "°C",
            "wind_unit": "km/h",
            "current": {
                "temperature": 23,
                "feels_like": 24,
                "humidity": 55,
                "wind_speed": 8,
                "condition": "Clear sky",
                "icon": "sun",
            },
            "forecast": [
                {
                    "weekday": "Friday",
                    "date": "Sep 25",
                    "high": 25,
                    "low": 18,
                    "condition": "Clear sky",
                    "icon": "sun",
                }
            ],
        }

        response = self.client.post("/", data={"city": "Kyoto", "unit": "celsius"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Kyoto, Kyoto, Japan", response.data)
        self.assertIn(b"Five-day forecast", response.data)
        self.assertIn(b"Clear sky", response.data)
        get_weather.assert_called_once_with("Kyoto", "celsius")

    @patch("app.get_weather")
    def test_empty_city_is_rejected_before_provider_call(self, get_weather):
        response = self.client.post("/", data={"city": "  ", "unit": "celsius"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Enter a city", response.data)
        get_weather.assert_not_called()

    @patch("app.get_weather", return_value=None)
    def test_unknown_city_shows_feedback(self, get_weather):
        response = self.client.post("/", data={"city": "Nowhere", "unit": "celsius"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"find that city", response.data)

    @patch("app.get_weather", side_effect=weather.WeatherError("offline"))
    def test_provider_error_shows_feedback_and_preserves_form(self, get_weather):
        response = self.client.post("/", data={"city": "Reykjavik", "unit": "fahrenheit"})
        self.assertEqual(response.status_code, 502)
        self.assertIn(b"temporarily unavailable", response.data)
        self.assertIn(b"value=\"Reykjavik\"", response.data)
        self.assertIn(b"value=\"fahrenheit\" selected", response.data)

    @patch("app.get_weather")
    def test_invalid_unit_is_rejected(self, get_weather):
        response = self.client.post("/", data={"city": "Boston", "unit": "kelvin"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Choose Celsius or Fahrenheit", response.data)
        get_weather.assert_not_called()


if __name__ == "__main__":
    unittest.main()
