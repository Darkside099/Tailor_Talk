import os
import json
import dateparser
from datetime import datetime, timedelta
from typing import TypedDict, Optional

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from calendar_api.calendar_api import get_upcoming_events, create_event

load_dotenv()
TIMEZONE = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Asia/Kolkata")


class AgentState(TypedDict, total=False):
    user_input: str
    response: str
    email: str


llm = ChatOpenAI(
    model="llama3-70b-8192",
    openai_api_base="https://api.groq.com/openai/v1",
    temperature=0.3,
)


def parse_llm_response(response: str) -> tuple[str, str, str]:
    try:
        parsed = json.loads(response)
        return (
            parsed.get("reply", "").strip(),
            parsed.get("action", "none").strip(),
            parsed.get("time", "").strip(),
        )
    except Exception as e:
        return "Sorry, I couldn't understand that.", "none", ""


def format_event_time(iso_string: str) -> str:
    try:
        dt = dateparser.parse(iso_string)
        return dt.strftime("%A, %b %d at %I:%M %p") if dt else iso_string
    except Exception:
        return iso_string


def handle_check_availability(reply: str, email: str) -> str:
    events = get_upcoming_events(email)
    if not events:
        return reply + "\nYou're all clear — no events found."

    event_list = []
    for event in events:
        time_str = format_event_time(event["start"]["dateTime"])
        summary = event.get("summary", "No Title")
        event_list.append(f"• {time_str} — {summary}")
    return reply + "\nHere are your upcoming events:\n" + "\n".join(event_list)


def handle_booking(reply: str, raw_time: str, email: str) -> str:
    parsed_time = dateparser.parse(
        raw_time,
        settings={
            "TIMEZONE": TIMEZONE,
            "TO_TIMEZONE": "UTC",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
        },
    )

    if not parsed_time or parsed_time < datetime.now(parsed_time.tzinfo):
        return (
            reply
            + "\n🕓 I need a clearer future time to schedule this. Can you say something like 'next Monday at 10 AM'?"
        )

    try:
        start_time = parsed_time
        end_time = start_time + timedelta(minutes=30)

        create_event(
            email=email,
            summary="Meeting via TailorTalk",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
        )

        local_time_str = start_time.astimezone().strftime("%A, %b %d at %I:%M %p")
        return reply + f"\n Booked: {local_time_str} ({TIMEZONE})"
    except Exception as e:
        return reply + f"\n Failed to schedule: {e}"


def llm_controller_node(state: AgentState) -> AgentState:
    user_input = state["user_input"]
    email = state["email"]

    system_prompt = """
You are TailorTalk, a conversational calendar assistant.

Your task is to:
1. Respond naturally to user input.
2. Identify calendar-related intent and return a JSON with:
   {
     "reply": "<assistant reply>",
     "action": "none" | "check_availability" | "book",
     "time": "<user mentioned time>"
   }
3. If the user input is unclear or lacks time info, set "action": "book" and provide a clarifying reply like "When should I schedule it?"

ALWAYS return valid JSON. Do NOT include explanations outside the JSON.
"""

    messages = [
        SystemMessage(content=system_prompt.strip()),
        HumanMessage(content=user_input),
    ]

    try:
        llm_response = llm.invoke(messages).content.strip()
        print("[LLM RAW OUTPUT]:", llm_response)
    except Exception as e:
        return {
            "user_input": user_input,
            "response": f" LLM error: {e}",
            "email": email,
        }

    reply, action, raw_time = parse_llm_response(llm_response)

    if action == "check_availability":
        reply = handle_check_availability(reply, email)
    elif action == "book":
        if not raw_time:
            reply += "\n When would you like to schedule it?"
        else:
            reply = handle_booking(reply, raw_time, email)

    return {"user_input": user_input, "response": reply, "email": email}


graph = StateGraph(AgentState)
graph.add_node("llm_controller", llm_controller_node)
graph.set_entry_point("llm_controller")
graph.add_edge("llm_controller", END)

app = graph.compile()
