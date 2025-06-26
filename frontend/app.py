import streamlit as st
import requests
from datetime import datetime


BACKEND_URL = st.secrets.get("BACKEND_URL")

st.set_page_config(page_title="TailorTalk", page_icon="🧵", layout="wide")


def init_state():
    defaults = {
        "chat_history": [],
        "timestamps": [],
        "email": None,
        "name": None,
        "logged_in": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_login_url() -> str:
    try:
        res = requests.get(f"{BACKEND_URL}/login")
        return res.json().get("login_url", "")
    except Exception as e:
        st.error(f"❌ Failed to get login URL: {e}")
        return ""


def logout_user():
    try:
        if st.session_state.email:
            requests.post(
                f"{BACKEND_URL}/logout", json={"email": st.session_state.email}
            )
    except Exception as e:
        st.warning(f"Logout failed: {e}")

    for key in list(st.session_state.keys()):
        del st.session_state[key]


def call_agent_api(user_input: str, email: str) -> str:
    try:
        res = requests.post(
            f"{BACKEND_URL}/agent",
            json={"user_input": user_input, "email": email},
        )
        if res.status_code == 200:
            return res.json().get("response", "🤔 Hmm, I didn’t get that.")
        elif res.status_code == 403:
            return "⚠️ Please login with Google first."
        return f"⚠️ Server error ({res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Connection error: {e}"


def handle_user_input(user_input: str):
    now = datetime.now().strftime("%I:%M %p")
    st.session_state.chat_history.append(("user", user_input))
    st.session_state.timestamps.append(now)

    with st.spinner("Tailor is thinking..."):
        reply = call_agent_api(user_input, st.session_state.email)

    st.session_state.chat_history.append(("assistant", reply))
    st.session_state.timestamps.append(datetime.now().strftime("%I:%M %p"))
    st.rerun()


def render_sidebar():
    with st.sidebar:
        st.markdown("## 🧵 TailorTalk")
        st.caption("AI-powered Google Calendar assistant")
        st.divider()

        if st.session_state.logged_in:
            st.markdown("### 👤 Logged In")
            st.success(f"**{st.session_state.name}**")
            st.caption(st.session_state.email)

            if st.button("🚪 Logout"):
                logout_user()
                st.rerun()

            st.divider()

        st.markdown("### 💡 Try saying:")
        st.markdown("- 📅 Book a meeting tomorrow at 2 PM")
        st.markdown("- 🗓️ What’s on my calendar this Friday?")
        st.markdown("- 📞 Schedule a call Monday at 11 AM")
        st.divider()
        st.markdown("🧠 Powered by **LangGraph**, **FastAPI**, and **Streamlit**")


def render_chat():
    for i, (role, message) in enumerate(st.session_state.chat_history):
        avatar = "🙂" if role == "user" else "🤖"
        timestamp = st.session_state.timestamps[i]
        with st.chat_message(role, avatar=avatar):
            st.markdown(message)
            st.caption(f"🕓 {timestamp}")


def check_auth_redirect():
    query = st.query_params
    if "email" in query and "name" in query:
        st.session_state.email = query["email"]
        st.session_state.name = query["name"]
        st.session_state.logged_in = True
        st.query_params.clear()


def main():
    init_state()
    check_auth_redirect()
    render_sidebar()

    st.title("💬 TailorTalk Assistant")
    st.caption("Chat naturally. I'll manage your schedule.")
    st.divider()

    if not st.session_state.logged_in:
        login_url = get_login_url()
        st.subheader("🔐 Login Required")
        st.markdown(
            f"[👉 Click here to login with Google]({login_url})", unsafe_allow_html=True
        )
        st.info("After logging in, you'll return here automatically.")
        return

    render_chat()
    user_input = st.chat_input("Type your message...")
    if user_input:
        handle_user_input(user_input)


if __name__ == "__main__":
    main()
