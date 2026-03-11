"""
app.py — FinOx Suite Entry Point
==================================
Auth-gated router: initialises DB, enforces login, then dynamically
imports and instantiates the selected feature module.

Run with:
    streamlit run app.py

IMPORTANT: st.set_page_config() MUST be the very first Streamlit call —
           at module level, never inside a function or conditional.
"""
from __future__ import annotations

import importlib

import streamlit as st

from config.settings import (
    APP_ICON,
    APP_LAYOUT,
    APP_TITLE,
    FOOTER_HTML,
    GLOBAL_CSS,
    MODULE_REGISTRY,
)
from components.sidebar import Sidebar

# ---------------------------------------------------------------------------
# MUST be the absolute first Streamlit call — at module level, no conditions.
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=APP_LAYOUT,
)


# ---------------------------------------------------------------------------
# Initialise database (creates tables if they don't exist)
# ---------------------------------------------------------------------------

def _init_database() -> None:
    """Bootstrap the SQLite DB once per process."""
    if st.session_state.get("_db_initialised"):
        return
    try:
        from database.engine import init_db
        init_db()
        st.session_state["_db_initialised"] = True
    except Exception as exc:
        st.error(f"⚠️ Database initialisation failed: {exc}")
        st.stop()


# ---------------------------------------------------------------------------
# Dynamic module loader
# ---------------------------------------------------------------------------

def _load_module_class(module_key: str):
    """
    Dynamically import and return the class for the selected module key.

    Parameters
    ----------
    module_key : str
        A key from MODULE_REGISTRY (e.g. '🏠 Home').

    Returns
    -------
    type
        The module class, uninstantiated.
    """
    entry      = MODULE_REGISTRY[module_key]
    mod_path   = entry["module"]
    class_name = entry["class"]
    module     = importlib.import_module(mod_path)
    return getattr(module, class_name)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def _render_footer() -> None:
    st.markdown("---")
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

def main() -> None:
    """Application entry point."""
    # ── Step 1: Inject global CSS on every rerun ──────────────────────────────
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Step 2: Bootstrap the database ───────────────────────────────────────
    _init_database()

    # ── Step 3: Enforce authentication gate ───────────────────────────────────
    from core.auth import is_authenticated, render_auth_page
    if not is_authenticated():
        render_auth_page()
        return   # render_auth_page calls st.stop(), but return is defensive

    # ── Step 4: Render sidebar — returns selected module name + params dict ───
    sidebar          = Sidebar(list(MODULE_REGISTRY.keys()))
    selected, params = sidebar.render()

    # Inject the authenticated user's code into every module's params for
    # strict data isolation — modules must use this when querying the DB.
    params["user_code"] = st.session_state.get("finox_user_code", "")

    # ── Step 5: Dynamically load and render the selected module ───────────────
    try:
        ModuleClass     = _load_module_class(selected)
        module_instance = ModuleClass(params)
        module_instance.render()
    except Exception as exc:
        st.error(f"An error occurred while loading **{selected}**.")
        with st.expander("🐛 Error details (for debugging)"):
            st.exception(exc)

    _render_footer()


if __name__ == "__main__":
    main()
