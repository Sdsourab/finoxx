"""
core/auth.py  ·  FinOx Suite  (v5.0 — Ultra-Minimal Login Redesign)
====================================================================
Authentication helpers: register, login, logout, session guard.

render_auth_page() — v5.0 changes
------------------------------------
• Ultra-minimalistic design: pure black/near-black background
• Single crisp teal accent line — no animated orbs (cleaner)
• Clean sans-serif typography, generous whitespace
• Card: subtle border only, no heavy shadows or blur — true minimal
• Inputs: borderless with bottom-line only style (material-inspired)
• Button: flat solid teal, no gradients
• Tight, purposeful layout — every element earns its space

Session state keys managed here
---------------------------------
  finox_authenticated : bool
  finox_user_code     : str  (e.g. "FNOX-8A9B-C7D6")
  finox_user_email    : str
  finox_display_name  : str
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from database.engine import get_db
from database.models_auth import User

# ── Design tokens ─────────────────────────────────────────────────────────────
_TEAL  = "#00C2B2"
_NAVY  = "#0F2744"
_RED   = "#EF4444"
_GREEN = "#10B981"


# ===========================================================================
# Session helpers  (UNCHANGED — backward-compatible)
# ===========================================================================

def is_authenticated() -> bool:
    return bool(st.session_state.get("finox_authenticated", False))


def current_user_code() -> str:
    return str(st.session_state.get("finox_user_code", ""))


def _set_session(user) -> None:
    st.session_state["finox_authenticated"] = True
    st.session_state["finox_user_code"]     = user.user_code
    st.session_state["finox_user_email"]    = user.email
    st.session_state["finox_display_name"]  = user.display_name or user.email


def logout() -> None:
    for key in ("finox_authenticated", "finox_user_code",
                "finox_user_email", "finox_display_name"):
        st.session_state.pop(key, None)


# ===========================================================================
# DB operations  (UNCHANGED — backward-compatible)
# ===========================================================================

def register_user(email: str, password: str, display_name: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    with get_db() as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return False, "An account with this email already exists."
        user_code = User.generate_user_code()
        while db.query(User).filter(User.user_code == user_code).first():
            user_code = User.generate_user_code()
        user = User(
            email         = email,
            password_hash = User.hash_password(password),
            user_code     = user_code,
            display_name  = display_name.strip() or email.split("@")[0],
        )
        db.add(user)
    return True, user_code


def login_user(email: str, password: str) -> tuple[bool, str]:
    email = email.strip().lower()
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.verify_password(password):
            return False, "Invalid email or password."
        if not user.is_active:
            return False, "This account has been deactivated."
        user.last_login = datetime.now(timezone.utc)
        snapshot = {
            "user_code":    user.user_code,
            "email":        user.email,
            "display_name": user.display_name,
        }

    class _Snap:
        def __init__(self, d: dict) -> None:
            self.user_code    = d["user_code"]
            self.email        = d["email"]
            self.display_name = d["display_name"]

    _set_session(_Snap(snapshot))
    return True, "Login successful."


# ===========================================================================
# Auth page CSS  (v5.0 — Ultra-Minimal)
# ===========================================================================

_AUTH_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

/* ── Hide Streamlit chrome on auth page ── */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebar"],
footer {{
    display: none !important;
}}

/* ── Full-viewport pure dark background ── */
.stApp {{
    background: #080c12 !important;
}}

/* ── Subtle grid texture overlay ── */
.auth-backdrop {{
    position: fixed;
    inset: 0;
    background:
        linear-gradient(rgba(0,194,178,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,194,178,0.03) 1px, transparent 1px);
    background-size: 48px 48px;
    z-index: -1;
    pointer-events: none;
}}

/* ── Single accent glow — top-center ── */
.auth-glow {{
    position: fixed;
    top: -220px;
    left: 50%;
    transform: translateX(-50%);
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(0,194,178,0.10) 0%, transparent 65%);
    pointer-events: none;
    z-index: -1;
}}

/* ── Card container ── */
.auth-card {{
    width: 100%;
    max-width: 400px;
    background: #0d1117;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 44px 40px 36px;
    position: relative;
    margin: 0 auto;
}}

/* Teal top accent line */
.auth-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 40px; right: 40px;
    height: 1px;
    background: linear-gradient(90deg, transparent, {_TEAL}90, transparent);
    border-radius: 0 0 2px 2px;
}}

/* ── Logo block ── */
.auth-logo {{
    text-align: center;
    margin-bottom: 32px;
}}
.auth-logo-mark {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 48px; height: 48px;
    border-radius: 12px;
    background: rgba(0,194,178,0.10);
    border: 1px solid rgba(0,194,178,0.20);
    font-size: 1.5rem;
    margin-bottom: 16px;
}}
.auth-logo h1 {{
    font-family: 'Inter', sans-serif;
    font-size: 1.60rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0 0 6px;
    letter-spacing: -0.5px;
    line-height: 1.2;
}}
.auth-logo h1 span {{
    color: {_TEAL};
}}
.auth-logo p {{
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: rgba(255,255,255,0.28);
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin: 0;
    font-weight: 500;
}}

/* ── Tab overrides ── */
.auth-card [data-baseweb="tab-list"] {{
    background: rgba(255,255,255,0.04) !important;
    border-radius: 8px !important;
    padding: 3px !important;
    gap: 3px !important;
    margin-bottom: 24px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}}
.auth-card [data-baseweb="tab"] {{
    font-family: 'Inter', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: rgba(255,255,255,0.40) !important;
    border-radius: 6px !important;
    padding: 7px 18px !important;
    transition: all 0.15s !important;
}}
.auth-card [aria-selected="true"] {{
    color: #FFFFFF !important;
    background: rgba(0,194,178,0.15) !important;
    border-bottom-color: transparent !important;
}}
.auth-card [data-baseweb="tab-border"],
.auth-card [data-baseweb="tab-highlight"] {{
    display: none !important;
}}

/* ── Section label ── */
.auth-section-h {{
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    font-weight: 500;
    color: rgba(255,255,255,0.65);
    margin: 0 0 20px;
    letter-spacing: 0;
}}

/* ── Label overrides ── */
.auth-card label,
.auth-card [data-testid="stWidgetLabel"] p {{
    font-family: 'Inter', sans-serif !important;
    font-size: 0.76rem !important;
    font-weight: 500 !important;
    color: rgba(255,255,255,0.50) !important;
    letter-spacing: 0.4px !important;
    text-transform: uppercase !important;
    margin-bottom: 6px !important;
}}

/* ── Input overrides — bottom-border only ── */
.auth-card input[type="text"],
.auth-card input[type="email"],
.auth-card input[type="password"],
.auth-card [data-testid="stTextInput"] input {{
    background: rgba(255,255,255,0.04) !important;
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.14) !important;
    border-radius: 8px !important;
    color: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 400 !important;
    height: 44px !important;
    padding: 0 12px !important;
    transition: border-color 0.15s, background 0.15s !important;
    caret-color: {_TEAL} !important;
}}
.auth-card input:focus,
.auth-card [data-testid="stTextInput"] input:focus {{
    border-bottom-color: {_TEAL} !important;
    background: rgba(0,194,178,0.05) !important;
    outline: none !important;
    box-shadow: none !important;
}}
.auth-card input::placeholder {{
    color: rgba(255,255,255,0.20) !important;
    font-weight: 400 !important;
}}

/* ── Button — flat solid ── */
.auth-card .stButton > button {{
    background: {_TEAL} !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    color: #000000 !important;
    letter-spacing: 0.1px !important;
    height: 44px !important;
    width: 100% !important;
    transition: opacity 0.15s, transform 0.15s !important;
    box-shadow: none !important;
    cursor: pointer !important;
}}
.auth-card .stButton > button:hover {{
    opacity: 0.88 !important;
    transform: none !important;
    box-shadow: none !important;
}}
.auth-card .stButton > button:active {{
    opacity: 0.75 !important;
    transform: scale(0.99) !important;
}}

/* ── Alert overrides ── */
.auth-card [data-testid="stAlertContainer"] {{
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    border-left-width: 3px !important;
    background: rgba(255,255,255,0.04) !important;
}}

/* ── Code reveal box ── */
.auth-code-reveal {{
    background: rgba(0,194,178,0.07);
    border: 1px solid rgba(0,194,178,0.20);
    border-radius: 10px;
    padding: 20px 22px;
    margin-top: 16px;
    text-align: center;
}}
.auth-code-reveal h4 {{
    font-family: 'Inter', sans-serif;
    color: rgba(255,255,255,0.60);
    margin: 0 0 10px;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}
.auth-code-val {{
    font-family: 'Courier New', Courier, monospace;
    font-size: 1.40rem;
    font-weight: 700;
    color: {_TEAL};
    letter-spacing: 4px;
    display: block;
    margin: 0 0 8px;
    word-break: break-all;
}}
.auth-code-note {{
    font-family: 'Inter', sans-serif;
    font-size: 0.71rem;
    color: rgba(255,255,255,0.30);
    margin: 0;
    line-height: 1.6;
}}

/* ── Feature pills below card ── */
.auth-pills {{
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-top: 20px;
    flex-wrap: wrap;
}}
.auth-pill {{
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.28);
    font-weight: 500;
    letter-spacing: 0.3px;
    display: flex;
    align-items: center;
    gap: 5px;
}}
.auth-pill::before {{
    content: '·';
    color: rgba(0,194,178,0.40);
    font-size: 1rem;
    line-height: 1;
}}
.auth-pill:first-child::before {{
    display: none;
}}

/* ── Divider ── */
.auth-divider {{
    border: none;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin: 18px 0;
}}

/* ── Section header utility ── */
.auth-form-label {{
    font-family: 'Inter', sans-serif;
    font-size: 0.80rem;
    font-weight: 500;
    color: rgba(255,255,255,0.55);
    margin: 0 0 18px;
}}

/* ── Mobile ── */
@media (max-width: 520px) {{
    .auth-card {{ padding: 32px 22px 28px; border-radius: 12px; max-width: 100%; }}
    .auth-logo h1 {{ font-size: 1.35rem; }}
    .auth-code-val {{ font-size: 1.15rem; letter-spacing: 3px; }}
}}
</style>
"""


# ===========================================================================
# Auth page renderer  (v5.0 — Ultra-Minimal)
# ===========================================================================

def render_auth_page() -> None:
    """
    Render the ultra-minimal full-page authentication UI.
    Clean, dark, purposeful — no unnecessary decoration.
    Calls st.stop() after rendering so the app router never proceeds.
    """

    # ── Inject CSS ──────────────────────────────────────────────────────────
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    # ── Minimal background elements ──────────────────────────────────────────
    st.markdown(
        "<div class='auth-backdrop'></div>"
        "<div class='auth-glow'></div>",
        unsafe_allow_html=True,
    )

    # ── Centre the card via columns ──────────────────────────────────────────
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown("<div class='auth-card'>", unsafe_allow_html=True)

        # ── Logo block ──────────────────────────────────────────────────────
        st.markdown(
            "<div class='auth-logo'>"
            "<div class='auth-logo-mark'>📈</div>"
            "<h1>Fin<span>Optiv</span></h1>"
            "<p>BI &amp; Data Science Suite</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Tabs ────────────────────────────────────────────────────────────
        tab_login, tab_reg = st.tabs(["Sign In", "Create Account"])

        # ── LOGIN TAB ───────────────────────────────────────────────────────
        with tab_login:
            st.markdown(
                "<p class='auth-section-h'>Welcome back</p>",
                unsafe_allow_html=True,
            )

            email_in    = st.text_input(
                "Email",
                placeholder="you@company.com",
                key="auth_login_email",
            )
            password_in = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                key="auth_login_pass",
            )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            if st.button("Sign In", key="auth_login_btn", use_container_width=True):
                if not email_in.strip():
                    st.error("Enter your email address.")
                elif not password_in:
                    st.error("Enter your password.")
                else:
                    ok, msg = login_user(email_in, password_in)
                    if ok:
                        st.success("Signing you in…")
                        st.rerun()
                    else:
                        st.error(msg)

        # ── REGISTER TAB ────────────────────────────────────────────────────
        with tab_reg:
            st.markdown(
                "<p class='auth-section-h'>Create your account</p>",
                unsafe_allow_html=True,
            )

            reg_name  = st.text_input(
                "Name",
                placeholder="Jane Smith",
                key="auth_reg_name",
            )
            reg_email = st.text_input(
                "Email",
                placeholder="you@company.com",
                key="auth_reg_email",
            )
            reg_pass  = st.text_input(
                "Password",
                type="password",
                placeholder="Minimum 6 characters",
                key="auth_reg_pass",
            )
            reg_pass2 = st.text_input(
                "Confirm password",
                type="password",
                placeholder="Repeat password",
                key="auth_reg_pass2",
            )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            if st.button("Create Account", key="auth_reg_btn", use_container_width=True):
                if not reg_name.strip():
                    st.error("Enter your name.")
                elif not reg_email.strip() or "@" not in reg_email:
                    st.error("Enter a valid email address.")
                elif len(reg_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                elif reg_pass != reg_pass2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(reg_email, reg_pass, reg_name)
                    if ok:
                        st.success("Account created.")
                        st.markdown(
                            f"<div class='auth-code-reveal'>"
                            f"<h4>Your User Code</h4>"
                            f"<span class='auth-code-val'>{msg}</span>"
                            f"<p class='auth-code-note'>"
                            f"Save this code — it uniquely identifies your data."
                            f"</p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        st.info("Switch to Sign In and log in with your new credentials.")
                    else:
                        st.error(msg)

        # Close card
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Feature pills ────────────────────────────────────────────────────
        st.markdown(
            "<div class='auth-pills'>"
            "<span class='auth-pill'>Gemini AI Insights</span>"
            "<span class='auth-pill'>16+ BI Modules</span>"
            "<span class='auth-pill'>Secure &amp; Private</span>"
            "<span class='auth-pill'>Real-Time Analytics</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.stop()