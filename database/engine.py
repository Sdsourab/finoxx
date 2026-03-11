"""
database/engine.py  ·  FinOx Suite
====================================
SQLAlchemy 2.0+ engine + session factory.
Single source of truth for all DB connections.

DEPLOYMENT FIX (v3.0)
----------------------
Streamlit Cloud mounts the repo at /mount/src/<user>/<repo>/ which can be
read-only in some configurations. The DB path now uses a writable fallback:
  1. Try  → project root (works locally and on most cloud setups)
  2. Try  → /tmp/        (always writable; data resets on dyno restart)

This prevents the "unable to open database file" OperationalError that
crashes the app immediately on Streamlit Community Cloud.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ---------------------------------------------------------------------------
# DB file location — writable path detection
# ---------------------------------------------------------------------------
def _find_writable_db_path() -> Path:
    """
    Return a writable path for the SQLite file.
    Tries the project root first; falls back to /tmp/ for cloud environments.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / "finox_data.db",   # local / cloud root
        Path("/tmp") / "finox_data.db",                              # guaranteed writable
    ]
    for p in candidates:
        try:
            # Test by touching a temp file in the same directory
            marker = p.parent / ".finox_write_test"
            marker.touch()
            marker.unlink()
            return p
        except (PermissionError, OSError):
            continue
    # Last resort – /tmp always exists on Linux
    return Path("/tmp") / "finox_data.db"


_DB_PATH = _find_writable_db_path()
_DB_URL  = f"sqlite:///{_DB_PATH}"


# ---------------------------------------------------------------------------
# Engine — cached as a shared resource (created once per server process)
# ---------------------------------------------------------------------------

@st.cache_resource
def _get_engine():
    """
    Create and return the SQLAlchemy engine.
    @st.cache_resource guarantees a single engine instance is shared across
    all Streamlit sessions and threads.
    """
    return create_engine(
        _DB_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )


# Backward-compatible module-level alias.
engine = _get_engine()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Helper: create all tables
# ---------------------------------------------------------------------------

@st.cache_resource
def init_db() -> None:
    """
    Create all tables declared via Base. Safe to call multiple times.
    @st.cache_resource guarantees this runs exactly once per server process.
    """
    from database import models_auth      # noqa: F401
    from database import models_features  # noqa: F401
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Context-manager helper
# ---------------------------------------------------------------------------

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Yield a DB session and guarantee cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()