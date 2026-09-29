import os

from flask import Flask, render_template, request

from weather import WeatherError, get_weather

app = Flask(__name__)


def render_page(city="", unit="celsius", weather=None, message=None, status=200):
    return render_template(
        "index.html",
        city=city,
        unit=unit,
        weather=weather,
        message=message,
    ), status


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_page()

    city = request.form.get("city", "").strip()
    unit = request.form.get("unit", "celsius")
    if unit not in ("celsius", "fahrenheit"):
        return render_page(city, message="Choose Celsius or Fahrenheit.", status=400)
    if not city:
        return render_page(message="Enter a city to see its weather.", status=400)
    if len(city) > 100:
        return render_page(city[:100], unit, message="City names must be 100 characters or fewer.", status=400)

    try:
        weather = get_weather(city, unit)
    except WeatherError:
        return render_page(
            city,
            unit,
            message="Weather data is temporarily unavailable. Please try again.",
            status=502,
        )

    if weather is None:
        return render_page(city, unit, message="We couldn't find that city. Try another name.")
    return render_page(city, unit, weather=weather)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
