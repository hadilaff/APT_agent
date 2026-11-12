import httpx
import time
import logging
import os

logger = logging.getLogger(__name__)

_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 1800  # 30 minutes (Open-Meteo updates hourly, no need to fetch more often)

# Vercel frontend proxies the weather request (avoids Open-Meteo rate limits on Render IPs)
WEATHER_PROXY_URL = os.environ.get(
    "WEATHER_PROXY_URL",
    "https://apt-agent.vercel.app/api/weather",
)

# Direct Open-Meteo as fallback
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

PARAMS = {
    "latitude": 36.84,
    "longitude": 10.25,
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
    "forecast_days": 3,
}


async def _fetch(url: str, params: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent": "APT-Agent/1.0"},
        )
        response.raise_for_status()
        return response.json()


async def get_weather():
    now = time.time()

    if _cache["data"] is not None and now - _cache["timestamp"] < CACHE_TTL:
        return _cache["data"]

    # Try Vercel proxy first, then fall back to direct Open-Meteo
    sources = [
        (WEATHER_PROXY_URL, {}),        # Vercel proxy (no params needed, baked in)
        (OPEN_METEO_URL, PARAMS),        # Direct fallback
    ]

    last_error = None
    for url, params in sources:
        try:
            data = await _fetch(url, params)
            _cache["data"] = data
            _cache["timestamp"] = now
            logger.info(f"Weather fetched from {url}")
            return data
        except httpx.HTTPStatusError as e:
            last_error = e
            logger.warning(f"Weather fetch failed from {url}: HTTP {e.response.status_code}")
            if e.response.status_code == 429 and _cache["data"] is not None:
                return _cache["data"]
        except Exception as e:
            last_error = e
            logger.warning(f"Weather fetch error from {url}: {e}")

    # Last resort: return stale cache
    if _cache["data"] is not None:
        logger.info("Returning stale cache as last resort")
        return _cache["data"]

    raise last_error
