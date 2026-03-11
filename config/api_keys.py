"""
config/api_keys.py  ·  FinOx Suite  (v5.3 — GitHub AI Models)
===============================================================
Key resolution order:
  1. st.session_state["GITHUB_PAT"]  — set via sidebar UI input (most reliable)
  2. st.secrets["GITHUB_PAT"]        — .streamlit/secrets.toml
  3. os.environ["GITHUB_PAT"]        — .env file (re-read fresh every call)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional


class KeySource(Enum):
    SESSION_STATE     = auto()
    STREAMLIT_SECRETS = auto()
    ENVIRONMENT       = auto()
    FALLBACK          = auto()
    NOT_FOUND         = auto()


@dataclass
class KeyStatus:
    provider: str
    source:   KeySource
    found:    bool
    preview:  str           = field(default="")
    error:    Optional[str] = field(default=None)

    @property
    def source_label(self) -> str:
        return {
            KeySource.SESSION_STATE:     "UI Input",
            KeySource.STREAMLIT_SECRETS: "Streamlit Secrets",
            KeySource.ENVIRONMENT:       ".env / Environment",
            KeySource.FALLBACK:          "Built-in Key",
            KeySource.NOT_FOUND:         "Not Configured",
        }[self.source]

    @property
    def status_icon(self) -> str:
        return "✅" if self.found else "❌"

    def __str__(self) -> str:
        if not self.found:
            return f"[{self.provider}] Key not found"
        return f"[{self.provider}] Loaded from {self.source_label} ({self.preview})"


def _mask(k: str) -> str:
    if len(k) > 12:
        return f"{k[:8]}...{k[-4:]}"
    return "●" * min(len(k), 8)


def _read_env_files() -> str:
    """
    Re-reads .env from disk on every call — no caching, no stale state.
    Tries multiple paths so it always works regardless of CWD.
    """
    this_file   = Path(__file__).resolve()
    project_dir = this_file.parent.parent   # finox_v2/

    candidates = [
        project_dir / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]

    seen = set()
    for p in candidates:
        rp = str(p.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        if not p.exists():
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "GITHUB_PAT" and v and v != "PASTE_YOUR_TOKEN_HERE":
                        return v
        except Exception:
            pass
    return ""


def _resolve(env_var: str, label: str, fallback: str = "") -> tuple[str, KeyStatus]:
    # 1 — Session state (set via sidebar UI — most reliable)
    try:
        import streamlit as st
        val = st.session_state.get(env_var, "")
        if val and str(val).strip():
            k = str(val).strip().strip('"').strip("'")
            if k and k != "PASTE_YOUR_TOKEN_HERE":
                return k, KeyStatus(label, KeySource.SESSION_STATE, True, _mask(k))
    except Exception:
        pass

    # 2 — Streamlit secrets (.streamlit/secrets.toml)
    try:
        import streamlit as st
        val = st.secrets.get(env_var, "")  # type: ignore[arg-type]
        if val and str(val).strip():
            k = str(val).strip().strip('"').strip("'")
            if k and k != "PASTE_YOUR_TOKEN_HERE":
                return k, KeyStatus(label, KeySource.STREAMLIT_SECRETS, True, _mask(k))
    except Exception:
        pass

    # 3 — Environment variable (re-read .env fresh every call)
    if env_var == "GITHUB_PAT":
        v = _read_env_files()
        if v:
            return v, KeyStatus(label, KeySource.ENVIRONMENT, True, _mask(v))

    val = os.environ.get(env_var, "").strip().strip('"').strip("'")
    if val and val != "PASTE_YOUR_TOKEN_HERE":
        return val, KeyStatus(label, KeySource.ENVIRONMENT, True, _mask(val))

    # 4 — Fallback
    if fallback and fallback.strip():
        return fallback.strip(), KeyStatus(label, KeySource.FALLBACK, True, _mask(fallback))

    return "", KeyStatus(label, KeySource.NOT_FOUND, False,
                         error=f"Add {env_var} to .env or .streamlit/secrets.toml")


# ── Public API ────────────────────────────────────────────────────────────────

def get_github_key() -> str:
    k, _ = _resolve("GITHUB_PAT", "GitHub AI Models")
    return k

def get_github_status() -> KeyStatus:
    _, s = _resolve("GITHUB_PAT", "GitHub AI Models")
    return s

# Backward-compat shims
def get_gemini_key() -> str:    return get_github_key()
def get_gemini_status():        return get_github_status()
def get_groq_key() -> str:      return get_github_key()
def get_groq_status():          return get_github_status()
def get_xai_key() -> str:       return get_github_key()
def get_xai_status():           return get_github_status()

def get_key(env_var: str, label: str = "") -> str:
    k, _ = _resolve(env_var, label or env_var)
    return k

def get_key_status(env_var: str, label: str = "") -> KeyStatus:
    _, s = _resolve(env_var, label or env_var)
    return s

@dataclass
class AllKeyStatuses:
    gemini: KeyStatus
    @property
    def xai(self) -> KeyStatus: return self.gemini
    @property
    def any_active(self) -> bool: return self.gemini.found

def get_all_statuses() -> AllKeyStatuses:
    return AllKeyStatuses(gemini=get_github_status())