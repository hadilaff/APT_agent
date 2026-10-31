import httpx

LATITUDE = 36.84
LONGITUDE = 10.25


async def get_weather():
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": (
            "temperature_2m,"
            "wind_speed_10m,"
            "wind_gusts_10m,"
            "wind_direction_10m,"
            "precipitation_probability,"
            "precipitation,"
            "weather_code"
        ),
        "timezone": "Africa/Tunis",
        "forecast_days": 2,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
        