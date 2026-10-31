import os
from dotenv import load_dotenv
from fastapi import FastAPI
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


WEATHER_KEYWORDS = (
    "row", "rowing", "ramer", "aviron", "weather", "météo", "meteo",
    "wind", "vent", "rain", "pluie", "forecast", "prévision", "prevision",
    "today", "tomorrow", "aujourd", "demain", "conditions", "session",
    "gust", "rafale", "wave", "température", "temperature", "knot", "km/h",
    "can i", "est-ce", "puis-je", "peux-je", "lac", "lake", "tunis",
)


def needs_weather(message: str) -> bool:
    text = message.lower()
    return any(keyword in text for keyword in WEATHER_KEYWORDS)


@app.post("/chat")
async def chat(request: ChatRequest):
    if not needs_weather(request.message):
        answer = await ask_agent(request.message, weather_data=None)
        return {"answer": answer}

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