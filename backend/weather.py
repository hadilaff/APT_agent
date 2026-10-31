import httpx
import time
import logging

logger = logging.getLogger(__name__)

LATITUDE = 36.84
LONGITUDE = 10.25

_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 600  # 10 minutes

HEADERS = {"User-Agent": "APT-Agent/1.0 (rowing weather assistant; contact: github.com/hadilaff)"}

PARAMS = {
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

# Two mirror URLs for Open-Meteo
URLS = [
    "https://api.open-meteo.com/v1/forecast",
    "https://api.open-meteo.com/v1/forecast",  # retry same with delay
]


async def get_weather():
    now = time.time()

    if _cache["data"] is not None and now - _cache["timestamp"] < CACHE_TTL:
        return _cache["data"]

    last_error = None

    for attempt, url in enumerate(URLS):
        try:
            if attempt > 0:
                time.sleep(2)  # wait 2 seconds before retry

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=PARAMS,
                    timeout=15,
                    headers=HEADERS,
                )
                response.raise_for_status()
                data = response.json()

            _cache["data"] = data
            _cache["timestamp"] = now
            return data

        except httpx.HTTPStatusError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e.response.status_code}")
            if e.response.status_code == 429 and _cache["data"] is not None:
                logger.info("Returning stale cache due to rate limit")
                return _cache["data"]
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} error: {e}")

    raise last_error
