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


@app.get("/")
async def root():
    return {"message": "APT Agent is running"}


@app.post("/chat")
async def chat(request: ChatRequest):

    weather = await get_weather()

    answer = await ask_agent(
        request.message,
        weather
    )

    return {
        "answer": answer
    }