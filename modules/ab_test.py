"""
modules/ab_test.py  ·  FinOx Suite
=====================================
Advanced A/B Test Analyzer with premium visualizations.
"""
from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div

try:
    from scipy import stats as _stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

_CUR   = "\u09f3"
_NAVY  = "#0B1F3A"
_TEAL  = "#00B4A6"
_AMBER = "#F5A623"
_RED   = "#E84855"
_GREEN = "#2ECC71"

_BASE = dict(
    template      = "plotly_white",
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font          = dict(family="'Segoe UI',Arial,sans-serif", size=12, color="#2D3748"),
    hoverlabel    = dict(bgcolor=_NAVY, font_color="#FFF", font_size=12),
    margin        = dict(t=52, b=22, l=12, r=12),
)


def _z_score_to_power(z_alpha: float, n: int, p1: float, p2: float) -> float:
    if n <= 0 or p1 <= 0 or p2 <= 0:
        return 0.0
    p_bar  = (p1 + p2) / 2
    se     = math.sqrt(2 * p_bar * (1 - p_bar) / n)
    effect = abs(p2 - p1)
    z_beta = effect / se - z_alpha if se > 0 else 0.0
    try:
        from scipy.stats import norm
        return float(norm.cdf(z_beta))
    except Exception:
        t = 1.0 / (1.0 + 0.2316419 * abs(z_beta))
        poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
                    + t * (-1.821255978 + t * 1.330274429))))
        cdf = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-z_beta ** 2 / 2) * poly
        return cdf if z_beta >= 0 else 1 - cdf


def _sample_size(p1: float) -> int:
    if p1 <= 0 or p1 >= 1:
        return 0
    z_a, z_b = 1.96, 0.842
    p2    = p1 * 1.10
    p_bar = (p1 + p2) / 2
    se_null = math.sqrt(2 * p_bar * (1 - p_bar))
    se_alt  = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    n = ((z_a * se_null + z_b * se_alt) / (p2 - p1)) ** 2 if p2 != p1 else 0
    return int(math.ceil(n))


class ABTestModule(BaseModule):
    PAGE_ICON  = "📊"
    PAGE_TITLE = "A/B Test Analyzer"

    def render(self) -> None:
        self._page_header(
            "📊 A/B Statistical Test Analyzer",
            "Enter visitor and conversion counts to evaluate statistical significance",
        )
        av, ac, bv, bc = self._render_inputs()
        cra = safe_div(ac, av)
        crb = safe_div(bc, bv)

        self._render_kpi_strip(cra, crb)
        st.markdown("---")

        tab1, tab2, tab3 = st.tabs([
            "📊 Conversion Chart",
            "〰️ Distribution Curves",
            "🔢 Sample Size Calculator",
        ])
        with tab1: self._tab_bar_chart(cra, crb)
        with tab2: self._tab_distributions(av, ac, bv, bc, cra, crb)
        with tab3: self._tab_sample_size(cra)

        st.markdown("---")
        self._render_insights(av, ac, bv, bc, cra, crb)

    def _render_inputs(self) -> tuple[int, int, int, int]:
        with st.container(border=True):
            col_a, col_b = st.columns(2, gap="large")
            with col_a:
                st.markdown(
                    f"<h4 style='color:{_NAVY};margin-bottom:8px'>🅰️ Group A — Control</h4>",
                    unsafe_allow_html=True,
                )
                av = st.number_input("Visitors A", 1, 10_000_000, 10_000, step=100, key="ab_av")
                ac = st.number_input("Conversions A", 0, int(av), 850, step=10, key="ab_ac")
            with col_b:
                st.markdown(
                    f"<h4 style='color:{_TEAL};margin-bottom:8px'>🅱️ Group B — Variant</h4>",
                    unsafe_allow_html=True,
                )
                bv = st.number_input("Visitors B", 1, 10_000_000, 10_000, step=100, key="ab_bv")
                bc = st.number_input("Conversions B", 0, int(bv), 980, step=10, key="ab_bc")
        return int(av), int(ac), int(bv), int(bc)

    def _render_kpi_strip(self, cra: float, crb: float) -> None:
        lift = (safe_div(crb, cra) - 1) if cra else 0.0
        diff = crb - cra
        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric("Conversion Rate A", f"{cra:.3%}")
        c2.metric("Conversion Rate B", f"{crb:.3%}", delta=f"{diff:+.3%}")
        c3.metric("Relative Lift",     f"{lift:+.2%}", delta="vs Control")
        c4.metric("Absolute Δ",        f"{diff:+.3%}")

    def _tab_bar_chart(self, cra: float, crb: float) -> None:
        winner = "B" if crb > cra else "A"
        diff   = abs(crb - cra)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Group A — Control"], y=[cra], name="Group A",
            marker=dict(color=[cra], colorscale=[[0, "#132843"], [1, _NAVY]],
                        showscale=False, line=dict(color=_NAVY, width=1.5)),
            text=f"<b>{cra:.3%}</b>", textposition="outside",
            hovertemplate="<b>Group A</b><br>CR: %{y:.3%}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=["Group B — Variant"], y=[crb], name="Group B",
            marker=dict(color=[crb], colorscale=[[0, "#004D45"], [1, _TEAL]],
                        showscale=False, line=dict(color=_TEAL, width=1.5)),
            text=f"<b>{crb:.3%}</b>", textposition="outside",
            hovertemplate="<b>Group B</b><br>CR: %{y:.3%}<extra></extra>",
        ))
        fig.update_layout(
            **_BASE, title=f"🏆 Winner: Group {winner}  (+{diff:.3%} absolute lift)",
            yaxis=dict(title="Conversion Rate", tickformat=".2%", gridcolor="#EDF2F7"),
            showlegend=False, height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    def _tab_distributions(self, av: int, ac: int, bv: int, bc: int,
                            cra: float, crb: float) -> None:
        x = np.linspace(
            min(cra, crb) - 3 * math.sqrt(cra * (1 - cra) / max(av, 1)),
            max(cra, crb) + 3 * math.sqrt(crb * (1 - crb) / max(bv, 1)),
            500,
        )
        se_a = math.sqrt(cra * (1 - cra) / max(av, 1))
        se_b = math.sqrt(crb * (1 - crb) / max(bv, 1))

        def _normal_pdf(xv: np.ndarray, mu: float, se: float) -> np.ndarray:
            if se == 0:
                return np.zeros_like(xv)
            return (1 / (se * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((xv - mu) / se) ** 2)

        ya = _normal_pdf(x, cra, se_a)
        yb = _normal_pdf(x, crb, se_b)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=ya, mode="lines", name="Group A",
            fill="tozeroy", fillcolor="rgba(11,31,58,0.12)",
            line=dict(color=_NAVY, width=2.5),
        ))
        fig.add_trace(go.Scatter(
            x=x, y=yb, mode="lines", name="Group B",
            fill="tozeroy", fillcolor="rgba(0,180,166,0.12)",
            line=dict(color=_TEAL, width=2.5),
        ))
        fig.add_vline(x=cra, line_dash="dash", line_color=_NAVY,
                      annotation_text=f"μA={cra:.3%}")
        fig.add_vline(x=crb, line_dash="dash", line_color=_TEAL,
                      annotation_text=f"μB={crb:.3%}")
        fig.update_layout(
            **_BASE, title="Sampling Distributions of Conversion Rate",
            xaxis=dict(title="Conversion Rate", tickformat=".2%"),
            yaxis=dict(title="Probability Density", gridcolor="#EDF2F7"),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

        p_bar   = safe_div(ac + bc, av + bv)
        se_pool = math.sqrt(p_bar * (1 - p_bar) * (safe_div(1, av) + safe_div(1, bv)))
        z_stat  = safe_div(crb - cra, se_pool)
        if _HAS_SCIPY:
            from scipy.stats import chi2_contingency
            tbl      = np.array([[ac, av - ac], [bc, bv - bc]])
            chi2, p_val, *_ = chi2_contingency(tbl, correction=False)
        else:
            p_val = max(0.0, 1 - abs(z_stat) / 3) if abs(z_stat) < 3 else 0.001
        power = _z_score_to_power(1.96, min(av, bv), cra, crb)
        sig   = p_val < 0.05

        c1, c2, c3 = st.columns(3)
        c1.metric("P-value", f"{p_val:.4f}", delta="✅ Significant" if sig else "❌ Not Significant")
        c2.metric("Z-statistic", f"{z_stat:.3f}")
        c3.metric("Statistical Power", f"{power:.1%}")

    def _tab_sample_size(self, cra: float) -> None:
        st.markdown("#### Minimum Sample Size Calculator")
        st.info("How many visitors do you need per group to detect a 10% relative lift at 80% power, α=0.05?")
        n = _sample_size(cra)
        st.metric("Required n per group", f"{n:,}")
        with st.container(border=True):
            st.markdown(
                f"**Interpretation:** At the current Group A conversion rate of **{cra:.3%}**, "
                f"you need at least **{n:,} visitors per group** to reliably detect a 10% "
                "relative improvement with 80% statistical power."
            )

    def _render_insights(self, av: int, ac: int, bv: int, bc: int,
                          cra: float, crb: float) -> None:
        lift  = (safe_div(crb, cra) - 1) if cra else 0.0
        p_bar = safe_div(ac + bc, av + bv)
        se    = math.sqrt(p_bar * (1 - p_bar) * (safe_div(1, av) + safe_div(1, bv)))
        z     = safe_div(crb - cra, se)
        self._insight_box(
            what=(
                f"Group A CR: {cra:.3%}, Group B CR: {crb:.3%}, "
                f"relative lift: {lift:+.2%}, Z-stat: {z:.2f}."
            ),
            recommendation=(
                "Group B is statistically significant — roll out the variant."
                if abs(z) >= 1.96
                else "Not yet significant. Collect more data before deciding."
            ),
            context_data={
                "Group A Visitors": av, "Group A Conversions": ac,
                "Group A CR": f"{cra:.3%}",
                "Group B Visitors": bv, "Group B Conversions": bc,
                "Group B CR": f"{crb:.3%}",
                "Relative Lift": f"{lift:+.2%}",
                "Z-statistic": f"{z:.3f}",
                "Significant": abs(z) >= 1.96,
            },
        )
