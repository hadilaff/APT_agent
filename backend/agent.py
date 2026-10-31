
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

from weather import get_weather

DEFAULT_TRAINING_HOUR = 17
TIMEZONE = ZoneInfo("Africa/Tunis")

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Check your backend/.env file."
    )

client = Groq(api_key=api_key)

TIMEZONE = ZoneInfo("Africa/Tunis")

app = FastAPI(title="APT Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.105:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


SYSTEM_PROMPT = """
You are APT Agent, a friendly weather assistant specialized in rowing
conditions at the Lake of Tunis.

PERSONALITY:
- Be warm, friendly, natural, and encouraging.
- Respond in the same language as the user: English, French, or Tunisian
  Arabic when possible.
- Start with a short overall assessment of the forecast.
- Use a few relevant emojis when helpful.
- Keep answers concise and practical.

ROWING ASSESSMENT:
- Base your assessment on the supplied weather data.
- If conditions genuinely look favorable, say so naturally, for example:
  "Les conditions semblent très favorables pour l'aviron !"
- If conditions are mixed, explain the main concern.
- If wind gusts are strong, highlight them even if average wind is moderate.
- Never automatically describe conditions as excellent.
- Never guarantee that rowing is safe.
- A weather forecast cannot confirm actual water conditions.

WEATHER DATA:
- Use only the supplied weather data.
- Never invent measurements or claim to have checked live lake conditions.
- Report wind speed and gusts in km/h and knots when available.
- When responding in French, write "nœuds" instead of "kn" or "knots".
- When responding in English, use "knots".
- Wind direction is reported in degrees and may be expressed using a
  compass direction.
- Mention temperature and precipitation when relevant.
- Clearly identify the forecast time.
- If the requested hour is unavailable, say so instead of substituting
  another hour without explaining.

Do not write the final disclaimer. The backend adds it.
"""


def kmh_to_knots(value):
    """Convert km/h to knots, preserving missing values."""
    if value is None:
        return None
    return round(value / 1.852, 1)


def requested_datetime(message):
    """
    Extract a requested hour and a simple date reference.
    Returns a local datetime, or None if no hour was found.
    """
    text = message.lower().strip()
    now = datetime.now(TIMEZONE)

    # Match 17:00, 17h, 5 PM, 5pm, 5:00 pm, 5 p.m.
    match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(h|am|pm|a\.m\.|p\.m\.)?\b",
        text,
    )

    if not match:
        requested_date = now.date()

        if any(word in text for word in ("day after tomorrow", "après-demain")):
            requested_date += timedelta(days=2)
        elif any(word in text for word in ("tomorrow", "demain", "ghodwa")):
            requested_date += timedelta(days=1)

        return datetime(
            requested_date.year,
            requested_date.month,
            requested_date.day,
            DEFAULT_TRAINING_HOUR,
            0,
            tzinfo=TIMEZONE,
            )

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = (match.group(3) or "").replace(".", "")

    # Avoid interpreting unrelated numbers as hours.
    if suffix in ("pm", "p.m"):
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + 12 if hour != 12 else 12
    elif suffix in ("am", "a.m"):
        if not 1 <= hour <= 12:
            return None
        hour = 0 if hour == 12 else hour
    elif suffix == "h":
        if not 0 <= hour <= 23:
            return None
    else:
        # A bare 5 is ambiguous; only accept 24-hour values here.
        if not 0 <= hour <= 23 or not re.search(r"\d{1,2}:\d{2}", text):
            return None

    if minute > 59:
        return None

    requested_date = now.date()

    if any(word in text for word in ("tomorrow", "demain", "ghodwa")):
        requested_date += timedelta(days=1)
    elif any(word in text for word in ("day after tomorrow", "après-demain")):
        requested_date += timedelta(days=2)

    return datetime(
        requested_date.year,
        requested_date.month,
        requested_date.day,
        hour,
        minute,
        tzinfo=TIMEZONE,
    )


def select_hourly_weather(weather_data, target_datetime):
    """Select the closest exact forecast hour and add knot conversions."""
    hourly = weather_data.get("hourly", {})
    times = hourly.get("time", [])

    target_string = target_datetime.strftime("%Y-%m-%dT%H:00")

    if target_string not in times:
        return None

    index = times.index(target_string)

    def value_for(key):
        values = hourly.get(key, [])
        return values[index] if index < len(values) else None

    wind_speed = value_for("wind_speed_10m")
    wind_gusts = value_for("wind_gusts_10m")

    return {
        "forecast_time": target_string,
        "timezone": weather_data.get("timezone", "Africa/Tunis"),
        "temperature_c": value_for("temperature_2m"),
        "wind_speed_kmh": wind_speed,
        "wind_speed_knots": kmh_to_knots(wind_speed),
        "wind_gusts_kmh": wind_gusts,
        "wind_gusts_knots": kmh_to_knots(wind_gusts),
        "wind_direction_degrees": value_for("wind_direction_10m"),
        "precipitation_probability_percent": value_for(
            "precipitation_probability"
        ),
        "precipitation_mm": value_for("precipitation"),
        "weather_code": value_for("weather_code"),
    }


def make_disclaimer(user_message):
    """Choose a disclaimer based on common French language markers."""
    text = user_message.lower()

    french_markers = (
        "météo", "vent", "ramer", "aviron", "aujourd'hui",
        "demain", "conditions", "pluie", "est-ce", "peux-je",
        "est ce", "quelle", "comment", "à quelle",
    )

    is_french = any(marker in text for marker in french_markers)

    if is_french:
        return (
            "⚠️ Ces prévisions météo ne sont pas fiables à 100 %. "
            "La météo peut changer à tout moment. "
            "Veuillez vérifier auprès du coach Riadh avant d'aller ramer."
        )

    return (
        "⚠️ These weather results are not 100% reliable. "
        "The weather can change at any time. "
        "Please check with Coach Riadh before going rowing."
    )


async def ask_agent(user_message: str, weather_data: dict | None) -> str:
    if weather_data is None:
        # Small talk — no weather needed
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()

    target = requested_datetime(user_message)

    if target is None:
        # No specific hour: provide the current local hour's forecast.
        now = datetime.now(TIMEZONE)
        target = now.replace(
            hour=DEFAULT_TRAINING_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )

    selected_weather = select_hourly_weather(weather_data, target)

    if selected_weather is None:
        return (
            "Sorry, I couldn't find an hourly forecast for that time. "
            "Please try another hour or date.\n\n"
            + make_disclaimer(user_message)
        )

    prompt = f"""
Forecast for rowing at the Lake of Tunis:

{selected_weather}

User question:
{user_message}

Answer using only the supplied forecast values. Give a friendly overall
assessment, then explain the wind speed, gusts, and direction. Include
both km/h and knots when those values are available. Be honest about
uncertainty and do not guarantee that rowing is safe.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    answer = (response.choices[0].message.content or "").strip()

    # Prevent duplicate disclaimers if the model includes one anyway.
    answer = re.sub(
        r"(?im)^.*(?:weather results are not 100% reliable|"
        r"prévisions météo ne sont pas fiables à 100 %).*$",
        "",
        answer,
    ).strip()

    return f"{answer}\n\n{make_disclaimer(user_message)}"


@app.post("/chat")
async def chat(request: ChatRequest):
    weather = await get_weather()
    answer = await ask_agent(request.message, weather)
    return {"answer": answer}
