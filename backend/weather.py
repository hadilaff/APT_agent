import httpx
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("Africa/Tunis")
_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 600  # 10 minutes

# wttr.in has no rate limits and works from any IP
WTTR_URL = "https://wttr.in/36.84,10.25?format=j1"


def _parse_wttr(raw: dict) -> dict:
    """Convert wttr.in JSON into the same hourly format the agent expects."""
    hourly_times = []
    hourly_temp = []
    hourly_wind = []
    hourly_gusts = []
    hourly_dir = []
    hourly_precip_prob = []
    hourly_precip = []
    hourly_code = []

    for day in raw.get("weather", []):
        date_str = day["date"]  # e.g. "2026-11-18"
        for h in day.get("hourly", []):
            # wttr.in time is "0", "300", "600" ... "2100" (minutes from midnight)
            minutes = int(h["time"])
            hour = minutes // 100
            dt_str = f"{date_str}T{hour:02d}:00"
            hourly_times.append(dt_str)
            hourly_temp.append(float(h["tempC"]))
            hourly_wind.append(float(h["windspeedKmph"]))
            hourly_gusts.append(float(h["WindGustKmph"]))
            hourly_dir.append(float(h["winddirDegree"]))
            hourly_precip_prob.append(float(h["chanceofrain"]))
            hourly_precip.append(float(h["precipMM"]))
            hourly_code.append(int(h["weatherCode"]))

    return {
        "timezone": "Africa/Tunis",
        "hourly": {
            "time": hourly_times,
            "temperature_2m": hourly_temp,
            "wind_speed_10m": hourly_wind,
            "wind_gusts_10m": hourly_gusts,
            "wind_direction_10m": hourly_dir,
            "precipitation_probability": hourly_precip_prob,
            "precipitation": hourly_precip,
            "weather_code": hourly_code,
        },
    }


async def get_weather():
    now = time.time()

    if _cache["data"] is not None and now - _cache["timestamp"] < CACHE_TTL:
        return _cache["data"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                WTTR_URL,
                timeout=15,
                headers={"User-Agent": "APT-Agent/1.0 (rowing assistant Lac de Tunis)"},
            )
            response.raise_for_status()
            raw = response.json()

        data = _parse_wttr(raw)
        _cache["data"] = data
        _cache["timestamp"] = now
        logger.info("Weather fetched from wttr.in")
        return data

    except Exception as e:
        logger.warning(f"Weather fetch error: {e}")
        if _cache["data"] is not None:
            logger.info("Returning stale cache")
            return _cache["data"]
        raise
