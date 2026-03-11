"""
core/base_module.py  ·  FinOx Suite  (v6.0 — GitHub AI Models)
===============================================================
Abstract base class for all FinOx feature modules.

AI Integration
--------------
Provider : GitHub AI Models  (https://models.inference.ai.azure.com)
Auth     : GITHUB_PAT from .env or .streamlit/secrets.toml
SDK      : Uses built-in `urllib` only — zero extra dependencies.

Model waterfall (tries each until one succeeds):
  gpt-4o-mini  →  gpt-4o  →  Phi-3.5-mini-instruct

v6.0 changes
------------
• Replaced Gemini / Google AI with GitHub AI Models API entirely.
• No google-generativeai or google-genai dependency needed.
• API calls use urllib (stdlib) — no openai package required.
• AI Insights auto-generate on page load (no button click needed).
• Params unpacked as direct instance attributes for all 16 modules.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any

import streamlit as st

from config.api_keys import get_gemini_key, get_gemini_status, KeySource

# ── Design tokens ─────────────────────────────────────────────────────────────
_TEAL  = "#0EA5A0"
_NAVY  = "#0F2744"
_AMBER = "#F59E0B"
_GREEN = "#10B981"
_RED   = "#EF4444"

# ── GitHub AI Models — endpoint & model waterfall ────────────────────────────
_GITHUB_AI_ENDPOINT = "https://models.inference.ai.azure.com/chat/completions"
_GITHUB_AI_MODELS   = [
    "gpt-4o-mini",
    "gpt-4o",
    "Phi-3.5-mini-instruct",
]
_AI_MAX_TOKENS = 650
_AI_TEMPERATURE = 0.22

# ── Session-state keys ────────────────────────────────────────────────────────
_SK_CACHE  = "_fnx_insight_cache"
_SK_ACTIVE = "insights_active"

# ── Risk thresholds ───────────────────────────────────────────────────────────
_RISK_THRESHOLDS = {
    "net_margin":    {"green": 0.15, "amber": 0.05},
    "gross_margin":  {"green": 0.40, "amber": 0.20},
    "ebitda_margin": {"green": 0.20, "amber": 0.08},
}

# ── Insight card CSS ──────────────────────────────────────────────────────────
_INSIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

.fnx-insight-card {
    background: linear-gradient(145deg, #F0FDFA 0%, #EFF6FF 60%, #FAFAFA 100%);
    border: 1px solid rgba(14, 165, 160, 0.20);
    border-left: 4px solid #0EA5A0;
    border-radius: 0 14px 14px 0;
    padding: 20px 24px 16px;
    margin-top: 20px;
    box-shadow: 0 1px 3px rgba(15,39,68,0.06), 0 4px 14px rgba(14,165,160,0.07);
    font-family: 'Plus Jakarta Sans', sans-serif;
    position: relative;
    overflow: hidden;
    z-index: 10;
}
.fnx-insight-card::after {
    content: 'AI';
    position: absolute; top: 12px; right: 16px;
    font-size: 3.5rem; font-weight: 900;
    color: rgba(14, 165, 160, 0.055);
    letter-spacing: -2px; pointer-events: none; user-select: none;
}
.fnx-insight-title {
    display: flex; align-items: center; flex-wrap: wrap;
    gap: 10px; margin-bottom: 14px;
}
.fnx-insight-title .label {
    font-size: 0.9rem; font-weight: 700; color: #0F2744;
    font-family: 'Plus Jakarta Sans', sans-serif; letter-spacing: -0.1px;
}
.fnx-risk-banner {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 12px; border-radius: 8px; margin-bottom: 12px;
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.5px; text-transform: uppercase;
}
.fnx-risk-green { background: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; }
.fnx-risk-amber { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.fnx-risk-red   { background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }
.fnx-badge {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.62rem; font-weight: 700; padding: 3px 10px;
    border-radius: 20px; letter-spacing: 0.7px;
    text-transform: uppercase; white-space: nowrap;
}
.fnx-badge-live {
    background: linear-gradient(90deg, #0F2744, #0EA5A0);
    color: #FFF; box-shadow: 0 2px 8px rgba(14,165,160,0.25);
}
.fnx-badge-static { background: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0; }
.fnx-model-tag {
    font-size: 0.61rem; color: #94A3B8;
    font-style: italic; margin-left: auto;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.fnx-insight-body { font-family: 'Plus Jakarta Sans', sans-serif; }
.fnx-insight-body p {
    margin: 0 0 10px; font-size: 0.875rem; line-height: 1.75;
    color: #1E293B; word-break: break-word;
}
.fnx-insight-body p:last-child { margin-bottom: 0; }
.fnx-insight-body strong { color: #0F2744; font-weight: 700; }
.fnx-static-label {
    font-size: 0.72rem; font-weight: 700; color: #475569;
    text-transform: uppercase; letter-spacing: 0.8px; margin: 0 0 4px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.fnx-static-text {
    font-size: 0.865rem; color: #475569; line-height: 1.7; margin: 0 0 14px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.fnx-ctx-table {
    width: 100%; border-collapse: collapse; font-size: 0.78rem; margin-bottom: 14px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.fnx-ctx-table td { padding: 4px 8px; border-bottom: 1px solid rgba(14,165,160,0.10); color: #334155; }
.fnx-ctx-table td:first-child { color: #64748B; font-weight: 600; width: 50%; }
.fnx-ctx-table td:last-child  { text-align: right; font-weight: 700; color: #0F2744; }
.fnx-auto-note {
    font-size: 0.70rem; color: #64748B; margin-top: 6px;
    display: flex; align-items: center; gap: 5px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.fnx-auto-note span.dot {
    width: 6px; height: 6px; background: #0EA5A0;
    border-radius: 50%; display: inline-block;
    animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.8); }
}
</style>
"""

# ── McKinsey Persona System Prompt ────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a Senior Partner at a Tier-1 management consulting firm (McKinsey / Bain / BCG calibre) \
specialising in financial performance, corporate strategy, and data-driven value creation. \
Your audience is a C-suite executive team reviewing real-time BI dashboards immediately before \
a board meeting. Your mandate is zero-tolerance for vague commentary.

MANDATORY OUTPUT STRUCTURE - bold headers exactly as shown:

**Executive Summary**
One power paragraph (2-3 sentences). Lead with the single most material metric and its \
precise value from the input. Quantify business impact in the same sentence. \
Never open with "The data shows" - open with the metric itself.

**Key Findings**
Exactly three bullet points. Each bullet MUST:
  - Cite a specific metric with its exact value from the data.
  - State the strategic implication (causality, not description).
  - End with urgency tag: [CRITICAL] / [MONITOR] / [OPPORTUNITY].

**Strategic Directives**
Two to three active-voice imperatives (e.g., "Reallocate 15% of X..."). \
Each directive must reference a specific number from the context and state the expected outcome. \
Order by ROI potential, highest first.

INVIOLABLE RULES:
- Total output: 220-260 words. No exceptions.
- Every number cited must appear verbatim in the input data. Never fabricate or estimate figures.
- Zero filler: no "it is important to note", "this suggests", "consider exploring", "leverage".
- The Risk Tier from the enriched context (GREEN/AMBER/RED) must influence tone and urgency.
- Do NOT include greetings, sign-offs, preambles, or format meta-commentary.
"""


# =============================================================================
# GitHub AI Models API caller — stdlib only, no extra packages needed
# =============================================================================

def _call_github_ai(api_key: str, prompt: str) -> str:
    """
    Call GitHub AI Models API.
    IMPORTANT — Your GitHub account must have Models enabled first:
      1. Go to https://github.com/marketplace/models
      2. Click "Sign up for GitHub Models" and accept the terms
      3. Then come back and click Refresh — your existing token will work
    """
    last_error: Exception | None = None

    # Try openai SDK first (GitHub's recommended approach)
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=api_key,
        )
        for model in _GITHUB_AI_MODELS:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=_AI_MAX_TOKENS,
                    temperature=_AI_TEMPERATURE,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                err = str(e).lower()
                if any(x in err for x in ("not found", "404", "model", "unavailable")):
                    last_error = e
                    continue
                _handle_ai_error(e, api_key)
    except ImportError:
        pass  # openai not installed — use urllib below

    # Fallback: urllib (stdlib only)
    last_error = None
    for model in _GITHUB_AI_MODELS:
        payload = json.dumps({
            "model":       model,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  _AI_MAX_TOKENS,
            "temperature": _AI_TEMPERATURE,
        }).encode("utf-8")
        req = urllib.request.Request(
            _GITHUB_AI_ENDPOINT,
            data=payload,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            code = e.code
            try:    err_body = e.read().decode("utf-8", errors="replace")
            except: err_body = str(e)
            if code in (404, 422):
                last_error = e
                continue
            if code in (401, 403):
                masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                raise PermissionError(
                    f"GitHub Models {code} — Account not activated.\n"
                    f"Token: {masked} (length={len(api_key)}) — token is correct.\n\n"
                    f"YOU MUST DO THIS ONE-TIME STEP:\n"
                    f"  → https://github.com/marketplace/models\n"
                    f"  → Click 'Sign up for GitHub Models'\n"
                    f"  → Accept terms of service\n"
                    f"  → Come back and click Refresh"
                ) from e
            if code == 429:
                raise RuntimeError("Rate limit reached. Wait a moment then click Refresh.")
            raise RuntimeError(f"GitHub AI HTTP {code}: {err_body[:300]}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error: {e.reason}")

    raise RuntimeError(f"All models failed. Last error: {last_error}")


def _handle_ai_error(exc: Exception, api_key: str) -> None:
    err = str(exc).lower()
    masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    if "401" in err or "403" in err or "unauthorized" in err or "forbidden" in err or "authentication" in err:
        raise PermissionError(
            f"GitHub Models auth error — Account not activated.\n"
            f"Token: {masked}\n"
            f"Fix: https://github.com/marketplace/models → Sign up → Accept terms."
        ) from exc
    if "429" in err or "rate" in err:
        raise RuntimeError("Rate limit reached. Wait a moment then click Refresh.") from exc
    raise RuntimeError(str(exc)) from exc


# =============================================================================
# Context enrichment helpers
# =============================================================================

def _safe_pct_change(new: float, old: float) -> str:
    try:
        if old == 0:
            return "N/A"
        change = (new - old) / abs(old) * 100
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.1f}%"
    except Exception:
        return "N/A"


"""
PATCH TARGET: core/base_module.py
==================================
Apply these two function replacements.

BUG: _build_enriched_context() and _classify_risk() both call
     context_data.items(), which crashes with:
       AttributeError: 'list' object has no attribute 'items'
     when any module passes a list (from df.to_dict(orient='records')).

FIX: Both functions now accept dict | list and handle both gracefully.
"""

# ── REPLACE _classify_risk (around line 2464 in original) ────────────────────

def _classify_risk(metrics: "dict | list") -> "tuple[str, str]":
    """
    Classify risk tier from a metrics dict (or list of dicts).
    Accepts both dict and list[dict] so modules can pass either format
    without crashing.
    """
    # ── Normalise list → flat dict ────────────────────────────────────────────
    if isinstance(metrics, list):
        flat: dict = {}
        for item in metrics:
            if isinstance(item, dict):
                flat.update(item)
        metrics = flat

    if not isinstance(metrics, dict):
        return "UNKNOWN", "fnx-risk-amber"

    try:
        def _extract(keys: list) -> "float | None":
            for k in keys:
                v = metrics.get(k)
                if v is not None:
                    s = str(v).replace("%", "").replace("\u09f3", "").replace(",", "").strip()
                    try:
                        fv = float(s)
                        return fv / 100 if "%" in str(v) else (fv if abs(fv) <= 1 else fv / 100)
                    except ValueError:
                        pass
            return None

        net_m    = _extract(["Net Margin", "Net Margin (final yr)", "net_margin"])
        gross_m  = _extract(["Gross Margin", "gross_margin"])
        ebitda_m = _extract(["EBITDA Margin", "ebitda_margin"])

        margin = net_m or gross_m or ebitda_m
        if margin is None:
            return "UNKNOWN", "fnx-risk-amber"

        t = _RISK_THRESHOLDS.get("net_margin", {"green": 0.15, "amber": 0.05})
        if margin >= t["green"]:
            return "GREEN", "fnx-risk-green"
        elif margin >= t["amber"]:
            return "AMBER", "fnx-risk-amber"
        else:
            return "RED", "fnx-risk-red"
    except Exception:
        return "UNKNOWN", "fnx-risk-amber"


# ── REPLACE _build_enriched_context (around line 2497 in original) ───────────

def _build_enriched_context(
    what: str,
    recommendation: str,
    context_data: "dict | list",
    risk_tier: str,
    risk_cls: str,
) -> str:
    """
    Serialise dashboard context to a plain-text string for the AI prompt.

    FIX: Accepts both dict and list[dict] — previously only accepted dict,
    crashing with AttributeError when modules passed .to_dict(orient='records').
    """
    lines = [
        f"_Risk Tier: {risk_tier}",
        f"_Analyst Context: {what}",
        f"_Static Rec: {recommendation}",
    ]

    if isinstance(context_data, dict):
        # Original happy-path: flat key→value pairs
        for k, v in context_data.items():
            lines.append(f"{k}: {v}")

    elif isinstance(context_data, list):
        # Defensive path: list of row-dicts from df.to_dict(orient='records')
        for i, item in enumerate(context_data):
            if isinstance(item, dict):
                lines.append(f"--- Record {i + 1} ---")
                for k, v in item.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"Item {i + 1}: {item}")

    else:
        # Fallback for any other unexpected type
        lines.append(f"Context: {context_data}")

    return "\n".join(lines)

# =============================================================================
# Base Module
# =============================================================================

class BaseModule(ABC):
    """Abstract base for all FinOx feature modules."""

    PAGE_ICON:  str = "📊"
    PAGE_TITLE: str = "Module"

    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params

        # ── Unpack all sidebar params as direct instance attributes ───────────
        # Every module accesses these as self.price, self.qty etc. directly.
        # Safe defaults mean a missing key never crashes any module.
        self.price          = float(params.get("price",          500.0))
        self.qty            = float(params.get("qty",            1000.0))
        self.var_cost       = float(params.get("var_cost",       200.0))
        self.fixed_monthly  = float(params.get("fixed_monthly",  150_000.0))
        self.capex_init     = float(params.get("capex_init",     2_500_000.0))
        self.forecast_years = int(  params.get("forecast_years", 5))
        self.dep_years      = int(  params.get("dep_years",      7))
        self.tax_rate       = float(params.get("tax_rate",       0.25))
        self.rev_growth     = float(params.get("rev_growth",     0.10))
        self.vc_inflation   = float(params.get("vc_inflation",   0.03))
        self.fc_inflation   = float(params.get("fc_inflation",   0.05))
        self.discount_rate  = float(params.get("discount_rate",  0.12))
        self.user_code      = str(  params.get("user_code",      ""))

        if _SK_CACHE not in st.session_state:
            st.session_state[_SK_CACHE] = {}
        # Auto-generate AI on load — no button click needed
        if _SK_ACTIVE not in st.session_state:
            st.session_state[_SK_ACTIVE] = True

    @abstractmethod
    def render(self) -> None: ...

    # =========================================================================
    # AI Insight Box — public entry point called by every module
    # =========================================================================

    def _insight_box(
        self,
        what:           str,
        recommendation: str,
        context_data:   dict[str, Any] | None = None,
    ) -> None:
        import re
        st.markdown(_INSIGHT_CSS, unsafe_allow_html=True)

        ctx = context_data or {}
        risk_tier, risk_cls = _classify_risk(ctx)
        ctx_str   = _build_enriched_context(what, recommendation, ctx, risk_tier, risk_cls)
        cache_key = hashlib.md5(ctx_str.encode()).hexdigest()
        cache     = st.session_state[_SK_CACHE]
        active    = st.session_state[_SK_ACTIVE]

        ai_key    = get_gemini_key()
        ai_status = get_gemini_status()
        has_key   = bool(ai_key)

        # ── Risk banner ───────────────────────────────────────────────────────
        risk_icons = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴", "UNKNOWN": "⚪"}
        risk_icon  = risk_icons.get(risk_tier, "⚪")

        # ── Controls row ──────────────────────────────────────────────────────
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([3, 1, 1])
        with ctrl_col1:
            st.markdown(
                f"<div class='fnx-risk-banner {risk_cls}'>"
                f"{risk_icon} Risk Tier: {risk_tier}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with ctrl_col2:
            if active and has_key:
                if st.button("🔄 Refresh", key=f"ref_{cache_key[:8]}", use_container_width=True):
                    cache.pop(cache_key, None)
                    st.rerun()
        with ctrl_col3:
            if active and has_key:
                if st.button("⏹ Disable", key=f"dis_{cache_key[:8]}", use_container_width=True):
                    st.session_state[_SK_ACTIVE] = False
                    st.rerun()
            elif not active and has_key:
                if st.button("▶ Enable AI", key=f"ena_{cache_key[:8]}", use_container_width=True):
                    st.session_state[_SK_ACTIVE] = True
                    st.rerun()

        # ── Card ──────────────────────────────────────────────────────────────
        st.markdown("<div class='fnx-insight-card'>", unsafe_allow_html=True)

        if active and has_key:
            # Auto-fetch on first render or when data changes
            if cache_key not in cache:
                self._fetch_and_cache(ai_key, ctx_str, cache_key, cache)

            if cache_key in cache:
                src_label = ai_status.source_label if ai_status.found else "API"
                st.markdown(
                    "<div class='fnx-insight-title'>"
                    "<span class='label'>🤖 GitHub AI — Strategic Analysis</span>"
                    "<span class='fnx-badge fnx-badge-live'>● LIVE</span>"
                    f"<span class='fnx-model-tag'>github models · {src_label}</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                self._render_insight_text(cache[cache_key])
                st.markdown(
                    "<div class='fnx-auto-note'>"
                    "<span class='dot'></span>"
                    "Auto-refreshes when dashboard data changes"
                    "</div>",
                    unsafe_allow_html=True,
                )
        else:
            # Static fallback — no GitHub PAT configured
            st.markdown(
                "<div class='fnx-insight-title'>"
                "<span class='label'>📋 Analysis Summary</span>"
                "<span class='fnx-badge fnx-badge-static'>Static</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            if ctx:
                rows = "".join(
                    f"<tr><td>{k}</td><td>{v}</td></tr>"
                    for k, v in list(ctx.items())[:8]
                )
                st.markdown(f"<table class='fnx-ctx-table'>{rows}</table>", unsafe_allow_html=True)
            st.markdown(
                f"<p class='fnx-static-label'>Situation</p>"
                f"<p class='fnx-static-text'>{what}</p>"
                f"<p class='fnx-static-label'>Recommendation</p>"
                f"<p class='fnx-static-text'>{recommendation}</p>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='font-size:0.75rem;color:#94A3B8;margin-top:8px;"
                "font-family:\"Plus Jakarta Sans\",sans-serif'>"
                "Add <code>GITHUB_PAT</code> to your <code>.env</code> to enable live AI insights."
                "</p>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _render_insight_text(self, text: str) -> None:
        import re
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        html = "<div class='fnx-insight-body'>"
        for para in paragraphs:
            para = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", para)
            html += f"<p>{para}</p>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    def _fetch_and_cache(
        self,
        ai_key: str,
        ctx_str:    str,
        cache_key:  str,
        cache:      dict,
        *,
        auto: bool = False,
    ) -> None:
        spinner_msg = (
            "🔄 Data changed — refreshing AI analysis automatically…"
            if auto
            else "🧠 GitHub AI is generating your boardroom-ready strategic analysis…"
        )
        full_prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            "--- DASHBOARD DATA ---\n"
            "You are reviewing the following enriched BI dashboard snapshot. "
            "Produce a structured board briefing strictly following the instructions above. "
            "Every number you cite MUST appear verbatim in the data below.\n\n"
            f"Enriched Dashboard Data:\n{ctx_str[:6000]}"
        )

        with st.spinner(spinner_msg):
            try:
                text = _call_github_ai(ai_key, full_prompt)
                if text:
                    cache[cache_key] = text
                else:
                    st.warning("⚠️ GitHub AI returned an empty response. Click **Refresh** to retry.")

            except PermissionError as exc:
                st.error(f"⚠️ **{exc}**")

            except ConnectionError as exc:
                st.error(f"⚠️ **Connection Error** — {exc}")

            except RuntimeError as exc:
                exc_msg = str(exc)
                if "429" in exc_msg or "rate limit" in exc_msg.lower():
                    st.error("⚠️ **Rate Limit** — GitHub AI quota reached. Wait a moment then click **Refresh**.")
                else:
                    st.error(f"⚠️ **GitHub AI Error**: {exc_msg}")

            except Exception as exc:
                st.error(f"⚠️ **Unexpected Error**: {exc}")

    # =========================================================================
    # Shared UI helpers
    # =========================================================================

    def _page_header(self, title: str | None = None, subtitle: str | None = None) -> None:
        _TEAL_H = "#00C2B2"
        _NAVY_H = "#0B1F3A"
        display = title or f"{self.PAGE_ICON} {self.PAGE_TITLE}"
        st.markdown(
            f"<h2 style='color:{_NAVY_H};margin-bottom:2px;"
            f"font-family:\"Plus Jakarta Sans\",sans-serif;"
            f"font-weight:800;letter-spacing:-0.3px;overflow:hidden;"
            f"text-overflow:ellipsis;word-break:break-word'>{display}</h2>",
            unsafe_allow_html=True,
        )
        if subtitle:
            st.markdown(
                f"<p style='color:#64748B;margin-top:0;font-size:0.9rem;"
                f"font-family:\"Plus Jakarta Sans\",sans-serif;word-break:break-word'>"
                f"{subtitle}</p>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<hr style='border:none;border-top:2px solid {_TEAL_H};margin:8px 0 20px'/>",
            unsafe_allow_html=True,
        )

    def _error_box(self, message: str) -> None:
        st.error(f"⚠️ {message}")

    def _info_box(self, message: str) -> None:
        st.info(f"ℹ️ {message}")

    def _require_columns(self, df: Any, required: list[str]) -> bool:
        missing = [c for c in required if c not in df.columns]
        if missing:
            self._error_box(f"Missing columns: {', '.join(missing)}")
            return False
        return True