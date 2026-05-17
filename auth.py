"""
auth.py — Session-based authentication for Streamlit
"""

import hashlib
import time
import logging
from typing import Optional, Tuple

import streamlit as st

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _verify(username: str, password: str) -> Optional[str]:
    """Return role if credentials valid, else None."""
    user = config.USERS.get(username)
    if not user:
        return None
    # simple plaintext comparison (replace with hashed in production)
    if password == user["password"]:
        return user["role"]
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  STREAMLIT SESSION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def init_session():
    """Ensure auth keys exist in st.session_state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "role" not in st.session_state:
        st.session_state.role = ""
    if "login_time" not in st.session_state:
        st.session_state.login_time = 0.0


def is_authenticated() -> bool:
    init_session()
    if not st.session_state.authenticated:
        return False
    # session timeout
    elapsed_min = (time.time() - st.session_state.login_time) / 60
    if elapsed_min > config.SESSION_TIMEOUT_MIN:
        logout()
        return False
    return True


def get_role() -> str:
    return st.session_state.get("role", "")


def is_admin() -> bool:
    return get_role() == "admin"


def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.login_time = 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def show_login_page():
    """Render the industrial-themed login page. Returns True when logged in."""
    init_session()

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;700&display=swap');

    .stApp { background: #0a0e1a; }
    .login-card {
        background: linear-gradient(135deg, #0f1628 0%, #141e35 100%);
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 2.5rem;
        max-width: 420px;
        margin: 6vh auto 0;
        box-shadow: 0 0 40px rgba(0,212,255,0.08), inset 0 0 20px rgba(0,0,0,0.3);
    }
    .login-title {
        font-family: 'Rajdhani', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: #00d4ff;
        text-align: center;
        letter-spacing: 2px;
        margin-bottom: 0.2rem;
    }
    .login-sub {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.7rem;
        color: #4a7aaa;
        text-align: center;
        letter-spacing: 3px;
        margin-bottom: 2rem;
    }
    .stTextInput > label { color: #7aaecc; font-family: 'Share Tech Mono', monospace; }
    .stTextInput > div > div > input {
        background: #0a1828;
        border: 1px solid #1e3a5f;
        color: #c8d8f0;
        border-radius: 6px;
    }
    </style>
    <div class="login-card">
        <div class="login-title">⚡ CONVEYORAI</div>
        <div class="login-sub">INDUSTRIAL MONITORING SYSTEM v1.0</div>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("---")
        username = st.text_input("Username", placeholder="admin / operator")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        if st.button("🔐 LOGIN", use_container_width=True):
            role = _verify(username, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.username      = username
                st.session_state.role          = role
                st.session_state.login_time    = time.time()
                logger.info("Login: %s (%s)", username, role)
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

        st.markdown(
            "<div style='text-align:center;color:#2a4a6a;font-size:0.7rem;margin-top:1rem'>"
            "Default — admin:admin123  |  operator:operator123</div>",
            unsafe_allow_html=True
        )
