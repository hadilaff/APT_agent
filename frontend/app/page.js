
"use client";

import { useState } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://apt-agent.onrender.com";

const suggestions = [
  {
    label: "Can I row at 17:00 today?",
    language: "en",
  },
  {
    label: "Est-ce que je peux ramer à 17h ?",
    language: "fr",
  },
  {
    label: "What about the wind gusts?",
    language: "en",
  },
];

export default function Home() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I'm APT Agent, your rowing weather assistant for Lac de Tunis. Ask me about wind, gusts, rain, or the forecast for your rowing session.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function sendMessage(event, suggestedText) {
    if (event) event.preventDefault();

    const message = (suggestedText ?? input).trim();

    if (!message || loading) return;

    setMessages((previous) => [
      ...previous,
      { role: "user", content: message },
    ]);

    setInput("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();

      if (!data.answer) {
        throw new Error("The API returned an empty response.");
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer,
        },
      ]);
    } catch (err) {
      console.error("APT Agent error:", err);

      setError(
        "Unable to reach APT Agent. Please check that the backend is running and the API URL is correct."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="chat-container">
        <header className="header">
          <div className="brand">
            <div className="logo">APT</div>

            <div>
              <h1>APT Agent</h1>
              <p>Rowing Weather Assistant</p>
            </div>
          </div>

          <div className="status">
            <span className="status-dot" />
            Lac de Tunis
          </div>
        </header>

        <section className="hero">
          <div className="weather-icon">🌤️</div>

          <p className="eyebrow">YOUR ROWING COMPANION</p>

          <h2>Is it a good day to row?</h2>

          <p className="hero-description">
            Get weather forecasts and understand wind conditions
            before your next rowing session.
          </p>

          <div className="feature-list">
            <span>💨 Wind & gusts</span>
            <span>🌡️ Temperature</span>
            <span>🌧️ Rain forecast</span>
          </div>

          {/* Mobile only: show the image instead */}
          <img
            src="/image.jpeg"
            alt="Lac de Tunis rowing"
            className="hero-mobile-image"
          />
        </section>

        <section className="conversation" aria-live="polite">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`message-row ${message.role}`}
            >
              {message.role === "assistant" && (
                <div className="message-avatar">A</div>
              )}

              <div className="message-bubble">
                {message.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row assistant">
              <div className="message-avatar">A</div>

              <div className="message-bubble typing">
                <span />
                <span />
                <span />
                <span className="sr-only">
                  APT Agent is checking the forecast
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}
        </section>

        <section className="suggestion-section">
          <p className="section-label">TRY ASKING</p>

          <div className="suggestions">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion.label}
                type="button"
                className="suggestion-button"
                disabled={loading}
                onClick={() =>
                  sendMessage(null, suggestion.label)
                }
              >
                {suggestion.label}
                <span aria-hidden="true">↗</span>
              </button>
            ))}
          </div>
        </section>

        <form
          className="composer"
          onSubmit={(event) => sendMessage(event)}
        >
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about your rowing conditions..."
            aria-label="Message APT Agent"
            disabled={loading}
          />

          <button
            type="submit"
            className="send-button"
            aria-label="Send message"
            disabled={loading || !input.trim()}
          >
            ↑
          </button>
        </form>

        <footer className="footer">
          <p>
            Forecasts can change at any time. Always check with
            Coach Riadh before going rowing.
          </p>
          <span>APT Agent · Powered by AI</span>
        </footer>
      </section>
    </main>
  );
}
