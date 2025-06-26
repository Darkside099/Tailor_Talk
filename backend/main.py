from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from agent import app as langgraph_app
from calendar_api.calendar_api import (
    start_google_auth,
    finish_google_auth,
    is_user_authenticated,
    _get_token_path
)
import os

app = FastAPI(
    title="TailorTalk AI",
    description="Conversational calendar assistant using Google OAuth",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tailortalkgit-aqb93ggrbwpdjhsngepge4.streamlit.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    user_input: str
    email: str

@app.get("/")
async def health_check():
    return {"status": "✅ TailorTalk API is live"}

@app.get("/login")
async def login():
    try:
        login_url = start_google_auth()
        return {"login_url": login_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create login URL: {e}")


@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    try:
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        email, name = finish_google_auth(code)

        frontend_url = f"https://tailortalkgit-aqb93ggrbwpdjhsngepge4.streamlit.app/?email={email}&name={name}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth error: {e}")

@app.post("/agent")
async def run_agent(request: AgentRequest):
    if not is_user_authenticated(request.email):
        raise HTTPException(status_code=403, detail="Login required.")

    try:
        result = langgraph_app.invoke(
            {"user_input": request.user_input, "email": request.email}
        )
        return {
            "response": result.get("response", "❓ Sorry, I didn’t understand that.")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")


@app.post("/logout")
async def logout(request: AgentRequest):
    try:
        path = _get_token_path(request.email)
        if os.path.exists(path):
            os.remove(path)
        return JSONResponse({"status": "✅ Logged out successfully."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout error: {e}")
