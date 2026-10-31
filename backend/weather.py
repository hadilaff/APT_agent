import httpx
import time

LATITUDE = 36.84
LONGITUDE = 10.25

_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 600  # 10 minutes


async def get_weather():
    now = time.time()

    if _cache["data"] is not None and now - _cache["timestamp"] < CACHE_TTL:
        return _cache["data"]

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
        response = await client.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

    _cache["data"] = data
    _cache["timestamp"] = now
    return data