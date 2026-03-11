"""
components/sidebar.py  ·  FinOx Suite  (v5.0 — GitHub AI Models)
=================================================================
Fully self-contained sidebar renderer.
Auth-aware: shows user badge and logout button when authenticated.

v5.0 change: AI status badge now shows GitHub AI Models instead of Gemini.
All other logic is identical to v4.1.

CACHING CHANGES (v2.0)
-----------------------
• _build_projection() — wrapped with @st.cache_data. This module-level helper
  is called on every sidebar render (i.e., every Streamlit rerun) when the
  projections chart toggle is enabled. Its single argument `p` is a dict of
  primitive float/int values, which Streamlit's content-based hasher handles
  natively. The function is a pure compound-growth loop with no side effects.

Returns
-------
(selected_module_name, params_dict)
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from config.api_keys import get_gemini_status
from utils.formatters import fmt, safe_div

_CUR  = "\u09f3"
_NAVY = "#0B1F3A"
_TEAL = "#00B4A6"

_DEFAULT_PARAMS: dict[str, Any] = {
    "price":          500.0,
    "qty":            1000.0,
    "var_cost":       200.0,
    "fixed_monthly":  150_000.0,
    "capex_init":     2_500_000.0,
    "forecast_years": 5,
    "dep_years":      7,
    "tax_rate":       0.25,
    "rev_growth":     0.10,
    "vc_inflation":   0.03,
    "fc_inflation":   0.05,
    "discount_rate":  0.12,
}


@st.cache_data
def _build_projection(p: dict) -> pd.DataFrame:
    """
    Build the multi-year projection DataFrame for the sidebar chart.

    @st.cache_data: The argument `p` is a dict whose values are all primitive
    Python types (float/int). Streamlit's content-based hasher recursively
    hashes dict contents, so this is fully safe. The function is a pure
    compound-growth loop — no UI calls, no session_state access, no side
    effects. Result is deterministic for any given parameter set.
    """
    base = p["price"] * p["qty"] * 12
    depr = p["capex_init"] / p["dep_years"] if p["dep_years"] > 0 else 0
    rows: list[dict] = []
    for i in range(int(p["forecast_years"])):
        rev    = base * (1 + p["rev_growth"]) ** i
        cogs   = p["var_cost"] * p["qty"] * 12 * (1 + p["vc_inflation"]) ** i
        fc     = p["fixed_monthly"] * 12 * (1 + p["fc_inflation"]) ** i
        ebitda = rev - cogs - fc
        net    = ebitda - depr - max(0.0, (ebitda - depr)) * p["tax_rate"]
        rows.append({
            "Year":       f"Y{i + 1}",
            "Revenue":    rev,
            "EBITDA":     ebitda,
            "Net Profit": max(0.0, net),
        })
    return pd.DataFrame(rows)


class Sidebar:
    """Renders the FinOx sidebar; returns (module_name, params_dict)."""

    def __init__(self, module_names: list[str]) -> None:
        self._names  = module_names
        self._params: dict[str, Any] = _DEFAULT_PARAMS.copy()

    def render(self) -> tuple[str, dict[str, Any]]:
        with st.sidebar:
            self._render_brand()
            self._render_user_badge()
            selected = st.selectbox("Navigate", self._names, key="sb_nav")
            st.markdown("---")
            self._render_ai_status()
            st.markdown("---")
            self._render_toggles()
            st.markdown("---")
            self._render_snapshot_or_chart()
        return selected, self._params

    # ── Brand header ──────────────────────────────────────────────────────────

    def _render_brand(self) -> None:
        st.markdown(
            "<div style='text-align:center;padding:10px 0 2px'>"
            "<span style='font-size:2.1rem'>📈</span><br>"
            "<span style='font-family:\"Plus Jakarta Sans\",sans-serif;font-size:1.6rem;"
            f"font-weight:800;color:#FFFFFF;letter-spacing:0.5px'>Finoptiv</span><br>"
            "<span style='font-size:0.68rem;color:#718096;letter-spacing:2.5px;"
            "text-transform:uppercase'>BI · Data Science Suite</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── User badge ────────────────────────────────────────────────────────────

    def _render_user_badge(self) -> None:
        from core.auth import is_authenticated, current_user_code, logout
        if not is_authenticated():
            return
        display = st.session_state.get("finox_display_name", "")
        code    = current_user_code()
        email   = st.session_state.get("finox_user_email", "")
        st.markdown(
            f"<div class='user-badge'>"
            f"<strong>👤 {display}</strong>"
            f"<span class='badge-email'>{email}</span>"
            f"<code>{code}</code>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("🚪 Log Out", use_container_width=True, key="sb_logout"):
            logout()
            st.rerun()

    # ── AI status indicator ───────────────────────────────────────────────────

    def _render_ai_status(self) -> None:
        import json, urllib.request, urllib.error
        from config.api_keys import KeySource as _KS, get_github_key

        status = get_gemini_status()
        key    = get_github_key()

        if status.found:
            source_icon = {
                _KS.STREAMLIT_SECRETS: "☁️",
                _KS.ENVIRONMENT:       "📁",
                _KS.SESSION_STATE:     "🔑",
            }.get(status.source, "🔑")
            st.markdown(
                "<div style='background:rgba(0,180,166,0.12);border:1px solid rgba(0,180,166,0.3);"
                "border-radius:8px;padding:10px 12px;'>"
                f"<p style='margin:0 0 4px;font-size:0.72rem;font-weight:700;"
                f"color:{_TEAL};text-transform:uppercase;letter-spacing:0.8px'>"
                "🤖 AI Insights — Active</p>"
                f"<p style='margin:0;font-size:0.7rem;color:#A0AEC0'>"
                f"GitHub AI Models &nbsp;{source_icon} {status.source_label}<br>"
                f"<code style='font-size:0.65rem'>{status.preview}</code></p>"
                "</div>",
                unsafe_allow_html=True,
            )
            # Test connection button
            if st.button("🔌 Test AI Connection", key="sb_test_ai", use_container_width=True):
                with st.spinner("Testing GitHub AI..."):
                    try:
                        payload = json.dumps({
                            "model":    "gpt-4o-mini",
                            "messages": [{"role":"user","content":"Say OK"}],
                            "max_tokens": 5,
                        }).encode()
                        req = urllib.request.Request(
                            "https://models.inference.ai.azure.com/chat/completions",
                            data=payload,
                            headers={"Authorization": f"Bearer {key}",
                                     "Content-Type": "application/json"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=15) as r:
                            body = json.loads(r.read())
                            reply = body["choices"][0]["message"]["content"]
                            st.success(f"✅ Connected! Response: {reply}")
                    except urllib.error.HTTPError as e:
                        err = e.read().decode("utf-8","replace")
                        masked = f"{key[:8]}...{key[-4:]}" if len(key)>12 else "***"
                        st.error(f"❌ HTTP {e.code} — Token used: {masked}\n{err[:300]}")
                    except Exception as e:
                        st.error(f"❌ {e}")
        else:
            st.markdown(
                "<div style='background:rgba(255,80,80,0.07);border:1px solid rgba(255,80,80,0.2);"
                "border-radius:8px;padding:10px 12px;'>"
                "<p style='margin:0 0 4px;font-size:0.72rem;font-weight:700;"
                "color:#718096;text-transform:uppercase;letter-spacing:0.8px'>"
                "🤖 AI Insights — Offline</p>"
                "<p style='margin:0;font-size:0.7rem;color:#718096;line-height:1.6'>"
                "<b style='color:#E53E3E'>Required one-time setup:</b><br>"
                "1. Go to <code>github.com/marketplace/models</code><br>"
                "2. Click <b>Sign up for GitHub Models</b><br>"
                "3. Accept terms of service<br>"
                "4. Paste your token below"
                "</p></div>",
                unsafe_allow_html=True,
            )
            typed = st.text_input(
                "Paste GITHUB_PAT",
                value="",
                type="password",
                key="sb_github_pat_input",
                placeholder="github_pat_...",
                help="Get token at github.com/settings/tokens (no scopes needed)",
            )
            if typed and typed.strip():
                st.session_state["GITHUB_PAT"] = typed.strip()
                st.rerun()
            st.markdown(
                "[🔗 Enable GitHub Models](https://github.com/marketplace/models)",
                unsafe_allow_html=False,
            )

    # ── Toggles ───────────────────────────────────────────────────────────────

    def _render_toggles(self) -> None:
        for key, default in [("show_config", False), ("show_chart", False)]:
            st.session_state.setdefault(key, default)
        st.session_state["show_config"] = st.toggle(
            "⚙️ Configuration", value=st.session_state["show_config"], key="sb_tog_cfg"
        )
        st.session_state["show_chart"] = st.toggle(
            "📈 Projections Chart", value=st.session_state["show_chart"], key="sb_tog_cht"
        )
        if st.session_state["show_config"]:
            self._render_business_map()
            self._render_financial_settings()
            if st.session_state["show_chart"]:
                self._render_growth_settings()

    # ── Business Map ──────────────────────────────────────────────────────────

    def _render_business_map(self) -> None:
        with st.expander("🌍 Business Map", expanded=True):
            self._params["price"] = st.number_input(
                f"Unit Price ({_CUR})", 1.0, 1e9,
                float(self._params["price"]), key="sb_price",
            )
            self._params["qty"] = st.number_input(
                "Monthly Quantity", 1.0, 1e9,
                float(self._params["qty"]), key="sb_qty",
            )
            self._params["var_cost"] = st.number_input(
                f"Unit Variable Cost ({_CUR})", 0.0, 1e9,
                float(self._params["var_cost"]), key="sb_vc",
            )
            self._params["fixed_monthly"] = st.number_input(
                f"Monthly Fixed Costs ({_CUR})", 0.0, 1e12,
                float(self._params["fixed_monthly"]), key="sb_fc",
            )
            self._params["capex_init"] = st.number_input(
                f"Initial CapEx ({_CUR})", 0.0, 1e12,
                float(self._params["capex_init"]), key="sb_capex",
            )

    # ── Financial Settings ────────────────────────────────────────────────────

    def _render_financial_settings(self) -> None:
        with st.expander("⚙️ Financial Settings"):
            self._params["forecast_years"] = st.slider(
                "Forecast Years", 1, 10,
                int(self._params["forecast_years"]), key="sb_fy",
            )
            self._params["dep_years"] = st.slider(
                "Depreciation Years", 1, 20,
                int(self._params["dep_years"]), key="sb_dy",
            )
            self._params["tax_rate"] = (
                st.slider(
                    "Tax Rate %", 0.0, 50.0,
                    float(self._params["tax_rate"]) * 100, key="sb_tax",
                ) / 100
            )

    # ── Growth & Valuation ────────────────────────────────────────────────────

    def _render_growth_settings(self) -> None:
        with st.expander("📊 Growth & Valuation"):
            self._params["rev_growth"] = (
                st.slider(
                    "Revenue Growth %", -20.0, 50.0,
                    float(self._params["rev_growth"]) * 100, key="sb_rg",
                ) / 100
            )
            self._params["vc_inflation"] = (
                st.slider(
                    "VC Inflation %", -10.0, 20.0,
                    float(self._params["vc_inflation"]) * 100, key="sb_vci",
                ) / 100
            )
            self._params["fc_inflation"] = (
                st.slider(
                    "FC Inflation %", -10.0, 20.0,
                    float(self._params["fc_inflation"]) * 100, key="sb_fci",
                ) / 100
            )
            self._params["discount_rate"] = (
                st.slider(
                    "Discount Rate %", 5.0, 25.0,
                    float(self._params["discount_rate"]) * 100, key="sb_dr",
                ) / 100
            )

    # ── Snapshot / Projection ─────────────────────────────────────────────────

    def _render_snapshot_or_chart(self) -> None:
        if st.session_state.get("show_chart", False):
            self._render_projection_chart()
        else:
            self._render_snapshot_kpis()

    def _render_snapshot_kpis(self) -> None:
        p        = self._params
        ann_rev  = p["price"] * p["qty"] * 12
        ann_prof = (p["price"] - p["var_cost"]) * p["qty"] * 12 - p["fixed_monthly"] * 12
        margin   = safe_div(ann_prof, ann_rev)
        st.markdown(
            "<p style='font-size:0.7rem;font-weight:700;color:#718096;"
            "letter-spacing:2px;text-transform:uppercase;margin-bottom:6px'>"
            "Company Snapshot</p>",
            unsafe_allow_html=True,
        )
        st.metric("Annual Revenue", fmt(ann_rev))
        st.metric("Annual Profit",  fmt(ann_prof))
        st.metric("Profit Margin",  f"{margin:.1%}")

    def _render_projection_chart(self) -> None:
        df = _build_projection(self._params)
        if df.empty:
            return
        df_m = df.melt(id_vars="Year", var_name="Metric", value_name="Amount")
        fig  = px.bar(
            df_m, x="Year", y="Amount", color="Metric", barmode="group",
            color_discrete_map={
                "Revenue": _TEAL, "EBITDA": "#F5A623", "Net Profit": _NAVY,
            },
            template="plotly_white",
        )
        fig.update_layout(
            height=200, showlegend=True,
            legend=dict(orientation="h", y=1.12, font_size=9, bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=28, b=5, l=0, r=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=10),
            yaxis=dict(tickprefix=_CUR, gridcolor="#EDF2F7"),
        )
        st.plotly_chart(fig, use_container_width=True)