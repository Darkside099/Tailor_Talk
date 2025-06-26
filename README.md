# 🧵 TailorTalk: AI-Powered Calendar Assistant

TailorTalk is a conversational assistant that seamlessly integrates with your **Google Calendar**. It understands natural language inputs to help you **check availability**, **book meetings**, and **manage your schedule**—all via an intuitive chat UI.

App link : https://tailortalkgit-aqb93ggrbwpdjhsngepge4.streamlit.app/
---

## ⚙️ Tech Stack

- 🔧 **Backend**: FastAPI + LangGraph
- 🤖 **AI Model**: Groq LLaMA3 (via LangChain)
- 📅 **Calendar Integration**: Google Calendar API (OAuth 2.0)
- 🧑‍💻 **Frontend**: Streamlit (with login-aware UI)

---

## 🗂️ Project Structure

tailor_talk/
├── backend/
│ ├── main.py # FastAPI entrypoint
│ ├── agent.py # LangGraph + LLM logic
│ └── calendar_api/
│ └── calendar_api.py # Google OAuth + Calendar API handlers
├── frontend/
│ └── streamlit_app.py # Main chat UI with login + memory
└── README.md

sequenceDiagram
    participant User
    participant Streamlit UI
    participant FastAPI
    participant Google OAuth
    participant Calendar API

    User->>Streamlit UI: Open App
    Streamlit UI->>FastAPI: GET /login
    FastAPI->>Google OAuth: Redirect user to consent screen
    Google OAuth->>FastAPI: Callback with auth code
    FastAPI->>Google Calendar API: Exchange code for token
    FastAPI->>Streamlit UI: Redirect with email+name
    Streamlit UI->>FastAPI: POST /agent (with email)
    FastAPI->>Calendar API: Perform action

┌──────────────┐      HTTP POST      ┌──────────────┐      LangGraph      ┌──────────────┐
│  Frontend UI │ ─────────────────▶ │  FastAPI API │ ─────────────────▶ │   Agent Node │
└──────────────┘                    └──────────────┘                      └─────┬────────┘
                                                                                  │
                                                                                  ▼
                                                                     ┌────────────────────┐
                                                                     │ Google Calendar API│
                                                                     └────────────────────┘


## 🚀 Run Locally

cd backend
uvicorn main:app --reload

cd frontend
streamlit run streamlit_app.py

---
## 💬 Sample Prompts

📅 "Book a meeting tomorrow at 2 PM"
🗓️ "What’s on my calendar this Friday?"
📞 "Schedule a call Monday at 11 AM"

---
## ✅ Features

✅ Secure Google Login (OAuth 2.0)
✅ Personalized session with cached auth
✅ Seamless LLM-based scheduling
✅ Works with vague or natural phrasing
✅ Auto-refreshes expired tokens
✅ One-click logout and session clearing

---
## 📌 Notes
Data is cached per session until logout
Tokens are stored securely under /tokens folder
This is a multi-user, production-ready template
