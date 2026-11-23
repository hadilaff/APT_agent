import os
from collections import defaultdict
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from weather import get_weather
from agent import ask_agent

load_dotenv()

app = FastAPI(title="APT Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Simple in-memory stats (resets on redeploy) ---
_stats = {
    "total_questions": 0,
    "questions_by_day": defaultdict(int),
    "question_types": defaultdict(int),  # weather / club / other
}


def record_request(message: str, kind: str):
    _stats["total_questions"] += 1
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _stats["questions_by_day"][day] += 1
    _stats["question_types"][kind] += 1


class ChatRequest(BaseModel):
    message: str


@app.get("/debug")
async def debug():
    try:
        from agent import ask_agent
        result = await ask_agent("hi", weather_data=None)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e), "type": type(e).__name__}


@app.get("/debug-weather")
async def debug_weather():
    try:
        data = await get_weather()
        times = data.get("hourly", {}).get("time", [])
        return {"status": "ok", "hours_available": len(times), "first": times[0] if times else None, "last": times[-1] if times else None}
    except Exception as e:
        return {"status": "error", "error": str(e), "type": type(e).__name__}


@app.get("/")
async def root():
    return {"message": "APT Agent is running"}


CLUB_KEYWORDS = (
    "coach", "riadh", "entraîneur", "entraineur",
    "apt", "association", "ligue", "championnat", "saison", "season",
)

SCHEDULE_KEYWORDS = (
    "horaire", "schedule", "heure d'entrainement", "heure de la seance",
    "heure de la séance", "quand est", "à quelle heure",
)

WEATHER_KEYWORDS = (
    "row", "rowing", "ramer", "aviron", "weather", "météo", "meteo",
    "wind", "vent", "rain", "pluie", "forecast", "prévision", "prevision",
    "today", "tomorrow", "aujourd", "demain", "conditions", "session",
    "gust", "rafale", "wave", "température", "temperature", "knot", "km/h",
    "can i", "est-ce", "puis-je", "peux-je", "lac", "lake", "tunis",
    "17h", "17:00", "indoor", "outdoor", "salle",
)


def needs_weather(message: str) -> bool:
    text = message.lower()
    # Pure club info (coach, leagues) — no weather needed
    if any(keyword in text for keyword in CLUB_KEYWORDS) and not any(keyword in text for keyword in WEATHER_KEYWORDS):
        return False
    # Pure schedule question — no weather needed
    if any(keyword in text for keyword in SCHEDULE_KEYWORDS) and not any(keyword in text for keyword in WEATHER_KEYWORDS):
        return False
    return any(keyword in text for keyword in WEATHER_KEYWORDS)


@app.get("/stats")
async def stats():
    return {
        "total_questions": _stats["total_questions"],
        "questions_by_day": dict(sorted(_stats["questions_by_day"].items())),
        "question_types": dict(_stats["question_types"]),
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    if not needs_weather(request.message):
        kind = "club" if any(k in request.message.lower() for k in CLUB_KEYWORDS) else "other"
        record_request(request.message, kind)
        answer = await ask_agent(request.message, weather_data=None)
        return {"answer": answer}

    record_request(request.message, "weather")
    try:
        weather = await get_weather()
    except Exception:
        return {
            "answer": (
                "⚠️ I'm unable to fetch the weather forecast right now. "
                "Please try again in a few minutes."
            )
        }

    answer = await ask_agent(request.message, weather)
    return {"answer": answer}