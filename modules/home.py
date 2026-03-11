"""
modules/home.py  ·  FinOx Suite  (v5.0 — Ultra-Modern Dashboard)
=================================================================
Executive Business Landscape — stunning, premium dashboard.

Sections
--------
  1. Hero banner  — Animated business health orb + KPI badges strip
  2. KPI grid     — 6 glassmorphism cards with gradient accents
  3. Revenue Intelligence — Beautiful area chart with gradient fill + margin overlay
  4. Cost Structure — Animated donut chart breakdown
  5. Monthly Snapshot — Waterfall + Sunburst
  6. Breakeven    — Gradient fills, profit zone, BEP marker
  7. Trend heatmap — YoY growth intensity grid
  8. AI insights card
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div, to_pct

# ── Design tokens ─────────────────────────────────────────────────────────────
_CUR    = "\u09f3"
_NAVY   = "#0B1F3A"
_TEAL   = "#00C2B2"
_TEAL2  = "#00E5D1"
_AMBER  = "#F59E0B"
_RED    = "#F43F5E"
_GREEN  = "#10B981"
_PURPLE = "#8B5CF6"
_BLUE   = "#3B82F6"
_SLATE  = "#64748B"
_WHITE  = "#FFFFFF"
_DARK   = "#0F172A"

# Plotly base layout — shared across all charts
_BASE = dict(
    template      = "plotly_white",
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font          = dict(
        family = "'DM Sans','Plus Jakarta Sans',sans-serif",
        size   = 12,
        color  = "#374151",
    ),
    hoverlabel = dict(
        bgcolor     = "#0B1F3A",
        font_color  = "#FFFFFF",
        font_size   = 13,
        bordercolor = _TEAL,
        font_family = "'DM Sans','Plus Jakarta Sans',sans-serif",
    ),
    margin = dict(t=44, b=16, l=8, r=8),
)

# ── Page-scoped CSS ───────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,300&display=swap');

/* ─────────── Root tokens ─────────── */
:root {
    --home-teal:    #00C2B2;
    --home-teal2:   #00E5D1;
    --home-navy:    #0B1F3A;
    --home-navy2:   #0d2845;
    --home-amber:   #F59E0B;
    --home-red:     #F43F5E;
    --home-green:   #10B981;
    --home-purple:  #8B5CF6;
    --home-blue:    #3B82F6;
    --fnx-font-head: 'Syne', sans-serif;
    --fnx-font-body: 'DM Sans', sans-serif;
}

/* ─────────── Base ─────────── */
section[data-testid="stVerticalBlock"] {
    font-family: var(--fnx-font-body);
}

/* ─────────── Hero Banner ─────────── */
.fnx-hero {
    background:
        radial-gradient(ellipse 80% 60% at 80% -10%, rgba(0,194,178,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 80% at -10% 80%, rgba(59,130,246,0.14) 0%, transparent 60%),
        linear-gradient(145deg, #040d1a 0%, #0b1f3a 45%, #0d2845 100%);
    border-radius: 24px;
    padding: 34px 36px 30px;
    margin-bottom: 32px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 28px;
    box-shadow:
        0 0 0 1px rgba(0,194,178,0.15),
        0 8px 16px rgba(0,0,0,0.18),
        0 24px 64px rgba(0,0,0,0.26),
        inset 0 1px 0 rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
}
/* animated shimmer stripe */
.fnx-hero::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 60%; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,229,209,0.7), transparent);
    animation: fnx-shimmer 4s ease-in-out infinite;
}
@keyframes fnx-shimmer {
    0%   { left: -100%; }
    60%  { left: 160%; }
    100% { left: 160%; }
}
/* corner mesh circles */
.fnx-hero::after {
    content: '';
    position: absolute;
    bottom: -100px; right: -60px;
    width: 360px; height: 360px;
    border-radius: 50%;
    border: 1px solid rgba(0,194,178,0.08);
    box-shadow:
        0 0 0 40px rgba(0,194,178,0.04),
        0 0 0 80px rgba(0,194,178,0.025),
        0 0 0 120px rgba(0,194,178,0.015);
    pointer-events: none;
}
.fnx-hero-left { position: relative; z-index: 1; }
.fnx-hero-left h2 {
    color: #FFFFFF;
    font-size: 1.55rem;
    font-weight: 800;
    margin: 0 0 6px;
    letter-spacing: -0.5px;
    font-family: var(--fnx-font-head);
}
.fnx-hero-left p {
    color: rgba(148,163,184,0.85);
    font-size: 0.80rem;
    margin: 0 0 20px;
    font-family: var(--fnx-font-body);
    letter-spacing: 0.2px;
}
.fnx-badge-row { display: flex; flex-wrap: wrap; gap: 8px; }
.fnx-hero-badge {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    color: rgba(203,213,225,0.85);
    font-size: 0.72rem;
    font-weight: 600;
    padding: 5px 14px;
    border-radius: 99px;
    font-family: var(--fnx-font-body);
    backdrop-filter: blur(8px);
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
    cursor: default;
}
.fnx-hero-badge:hover {
    background: rgba(0,194,178,0.20);
    border-color: rgba(0,194,178,0.45);
    color: #ffffff;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,194,178,0.20);
}

/* ─────────── Health Score Orb ─────────── */
.fnx-health {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    min-width: 100px;
    position: relative;
    z-index: 1;
}
.fnx-health-orb {
    width: 92px; height: 92px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    margin-bottom: 8px;
    animation: fnx-pulse-orb 3s ease-in-out infinite;
}
@keyframes fnx-pulse-orb {
    0%, 100% { box-shadow: var(--orb-glow-a); }
    50%       { box-shadow: var(--orb-glow-b); }
}
.fnx-health-orb .score {
    font-size: 2.1rem;
    font-weight: 900;
    line-height: 1.1;
    font-family: var(--fnx-font-head);
}
.fnx-health-orb .slash {
    font-size: 0.60rem;
    letter-spacing: 1px;
    font-weight: 600;
    opacity: 0.5;
}
.fnx-health .label {
    font-size: 0.60rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: rgba(0,194,178,0.80);
    margin-bottom: 6px;
    font-family: var(--fnx-font-body);
}
.fnx-health .status-badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 4px 14px;
    border-radius: 99px;
    font-family: var(--fnx-font-body);
    letter-spacing: 0.2px;
}

/* ─────────── Section Headers ─────────── */
.fnx-section {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 0 10px;
    border-bottom: 1.5px solid #E5E7EB;
    margin: 36px 0 22px;
    position: relative;
}
/* animated accent underline */
.fnx-section::after {
    content: '';
    position: absolute;
    bottom: -1.5px; left: 0;
    height: 2px;
    width: 60px;
    background: linear-gradient(90deg, var(--sec-color, #00C2B2), transparent);
    border-radius: 2px;
}
.fnx-section-icon {
    width: 42px; height: 42px;
    border-radius: 13px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.3);
}
.fnx-section-text h3 {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: #0B1F3A;
    font-family: var(--fnx-font-head);
    letter-spacing: -0.3px;
}
.fnx-section-text p {
    margin: 3px 0 0;
    font-size: 0.74rem;
    color: #6B7280;
    font-family: var(--fnx-font-body);
}

/* ─────────── KPI Grid ─────────── */
.fnx-kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 8px;
}
.fnx-kpi {
    background: #FFFFFF;
    border-radius: 20px;
    padding: 22px 22px 18px;
    border: 1px solid #EAECF0;
    box-shadow:
        0 1px 2px rgba(0,0,0,0.03),
        0 4px 16px rgba(0,0,0,0.055);
    position: relative;
    overflow: hidden;
    transition: transform 0.22s cubic-bezier(0.4,0,0.2,1), box-shadow 0.22s;
    cursor: default;
}
.fnx-kpi:hover {
    transform: translateY(-5px) scale(1.005);
    box-shadow:
        0 4px 10px rgba(0,0,0,0.07),
        0 16px 36px rgba(0,0,0,0.12);
}
/* Gradient top accent bar */
.fnx-kpi::before {
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    border-radius: 20px 20px 0 0;
}
.fnx-kpi.c-teal::before   { background: linear-gradient(90deg, #00C2B2 0%, #00E5D1 50%, #00C2B280 100%); }
.fnx-kpi.c-navy::before   { background: linear-gradient(90deg, #0B1F3A 0%, #1D4ED8 60%, #3B82F680 100%); }
.fnx-kpi.c-amber::before  { background: linear-gradient(90deg, #F59E0B 0%, #FCD34D 60%, #F59E0B80 100%); }
.fnx-kpi.c-green::before  { background: linear-gradient(90deg, #10B981 0%, #34D399 60%, #10B98180 100%); }
.fnx-kpi.c-red::before    { background: linear-gradient(90deg, #F43F5E 0%, #FB7185 60%, #F43F5E80 100%); }
.fnx-kpi.c-purple::before { background: linear-gradient(90deg, #8B5CF6 0%, #C4B5FD 60%, #8B5CF680 100%); }
/* Subtle glow blob */
.fnx-kpi::after {
    content: "";
    position: absolute;
    top: -30px; right: -30px;
    width: 110px; height: 110px;
    border-radius: 50%;
    opacity: 0.07;
    pointer-events: none;
    transition: opacity 0.22s;
}
.fnx-kpi:hover::after { opacity: 0.13; }
.fnx-kpi.c-teal::after   { background: #00C2B2; }
.fnx-kpi.c-navy::after   { background: #1D4ED8; }
.fnx-kpi.c-amber::after  { background: #F59E0B; }
.fnx-kpi.c-green::after  { background: #10B981; }
.fnx-kpi.c-red::after    { background: #F43F5E; }
.fnx-kpi.c-purple::after { background: #8B5CF6; }

.fnx-kpi-icon {
    width: 40px; height: 40px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.10rem;
    margin-bottom: 14px;
    flex-shrink: 0;
    transition: transform 0.22s;
}
.fnx-kpi:hover .fnx-kpi-icon { transform: scale(1.12) rotate(-3deg); }
.fnx-kpi.c-teal   .fnx-kpi-icon { background: rgba(0,194,178,0.12); }
.fnx-kpi.c-navy   .fnx-kpi-icon { background: rgba(11,31,58,0.08); }
.fnx-kpi.c-amber  .fnx-kpi-icon { background: rgba(245,158,11,0.12); }
.fnx-kpi.c-green  .fnx-kpi-icon { background: rgba(16,185,129,0.12); }
.fnx-kpi.c-red    .fnx-kpi-icon { background: rgba(244,63,94,0.12); }
.fnx-kpi.c-purple .fnx-kpi-icon { background: rgba(139,92,246,0.12); }
.fnx-kpi-lbl {
    font-size: 0.67rem;
    font-weight: 700;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 8px;
    font-family: var(--fnx-font-body);
}
.fnx-kpi-val {
    font-size: 1.75rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.15;
    letter-spacing: -0.8px;
    font-family: var(--fnx-font-head);
    word-break: break-all;
}
.fnx-kpi-sub {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-top: 10px;
}
.fnx-delta {
    font-size: 0.70rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 99px;
    display: inline-block;
    font-family: var(--fnx-font-body);
    letter-spacing: 0.1px;
}
.fnx-delta.pos { background: #ECFDF5; color: #047857; }
.fnx-delta.neg { background: #FFF1F2; color: #BE123C; }
.fnx-delta.neu { background: #EFF6FF; color: #1D4ED8; }
.fnx-kpi-ghost {
    position: absolute;
    bottom: 8px; right: 14px;
    font-size: 2.8rem;
    opacity: 0.04;
    pointer-events: none;
    user-select: none;
    transition: opacity 0.22s, transform 0.22s;
}
.fnx-kpi:hover .fnx-kpi-ghost { opacity: 0.09; transform: scale(1.1) rotate(8deg); }

/* ─────────── Chart Cards ─────────── */
.fnx-chart-card {
    background: #FFFFFF;
    border-radius: 20px;
    border: 1px solid #EAECF0;
    box-shadow:
        0 1px 3px rgba(0,0,0,0.04),
        0 4px 16px rgba(0,0,0,0.055);
    padding: 22px 24px 14px;
    margin-bottom: 16px;
    transition: box-shadow 0.22s;
    overflow: hidden;
    position: relative;
}
.fnx-chart-card:hover {
    box-shadow:
        0 2px 6px rgba(0,0,0,0.05),
        0 12px 32px rgba(0,0,0,0.09);
}
.fnx-chart-card .fnx-ct {
    font-size: 0.96rem;
    font-weight: 700;
    color: #0B1F3A;
    margin: 0 0 3px;
    font-family: var(--fnx-font-head);
    letter-spacing: -0.2px;
}
.fnx-chart-card .fnx-cs {
    font-size: 0.73rem;
    color: #9CA3AF;
    margin: 0 0 14px;
    font-family: var(--fnx-font-body);
}

/* ─────────── BEP mini-metrics ─────────── */
.fnx-bep-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 18px;
}
.fnx-bep-cell {
    background: linear-gradient(145deg, #F8FAFC, #FFFFFF);
    border: 1px solid #EAECF0;
    border-radius: 14px;
    padding: 16px 16px 14px;
    text-align: center;
    transition: all 0.22s cubic-bezier(0.4,0,0.2,1);
    cursor: default;
}
.fnx-bep-cell:hover {
    background: linear-gradient(145deg, #F0FDFA, #E6FFFE);
    border-color: rgba(0,194,178,0.40);
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(0,194,178,0.12);
}
.fnx-bep-cell .bv {
    font-size: 1.15rem;
    font-weight: 800;
    color: #0B1F3A;
    font-family: var(--fnx-font-head);
    letter-spacing: -0.3px;
}
.fnx-bep-cell .bl {
    font-size: 0.63rem;
    font-weight: 600;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
    font-family: var(--fnx-font-body);
}

/* ─────────── Responsive ─────────── */
@media (max-width: 900px) {
    .fnx-kpi-grid { grid-template-columns: repeat(2, 1fr); }
    .fnx-bep-row  { grid-template-columns: repeat(2, 1fr); }
    .fnx-hero     { flex-direction: column; align-items: center; }
}
@media (max-width: 600px) {
    .fnx-kpi-grid { grid-template-columns: 1fr; }
}
</style>
"""


class HomeModule(BaseModule):
    PAGE_ICON  = "🏠"
    PAGE_TITLE = "Executive Dashboard"

    # ── Entry point ───────────────────────────────────────────────────────────

    def render(self) -> None:
        st.markdown(_CSS, unsafe_allow_html=True)
        self._page_header(
            "🏠 Executive Business Landscape",
            "Live financial overview — driven by your sidebar parameters",
        )

        f = self._compute_financials()

        # 1 — Hero banner
        self._hero_banner(f)

        # 2 — KPI cards
        self._section("📊", "#00C2B2", "Key Performance Indicators",
                       "Six core financial metrics derived from current parameters")
        self._kpi_cards(f)

        # 3 — Revenue Intelligence (full width)
        self._section("📈", "#0B1F3A", "Revenue Intelligence",
                       f"{self.forecast_years}-year P&L projection at "
                       f"{self.rev_growth:.0%} annual growth")
        self._revenue_intelligence(f)

        # 4 — Monthly snapshot: waterfall | cost donut
        self._section("🔍", "#F59E0B", "Monthly Financial Snapshot",
                       "Single-month P&L waterfall and annual cost structure breakdown")
        col_l, col_r = st.columns([3, 2], gap="large")
        with col_l:
            self._waterfall(f)
        with col_r:
            self._cost_donut(f)

        # 5 — Breakeven
        self._section("📏", "#8B5CF6", "Breakeven Analysis",
                       "Units required per month before entering profit territory")
        self._breakeven(f)

        # 6 — Margin trend heatmap
        if self.forecast_years >= 2:
            self._section("🌡️", "#3B82F6", "Multi-Year Margin Heatmap",
                           "YoY growth intensity across key financial metrics")
            self._margin_heatmap(f)

        # 7 — AI insights
        self._insights(f)

    # =========================================================================
    # Financial engine
    # =========================================================================

    def _compute_financials(self) -> dict:
        rev       = self.price * self.qty * 12
        vc_tot    = self.var_cost * self.qty * 12
        gp        = rev - vc_tot
        fc_tot    = self.fixed_monthly * 12
        ebitda    = gp - fc_tot
        depr      = safe_div(self.capex_init, self.dep_years)
        ebit      = ebitda - depr
        tax       = max(0.0, ebit * self.tax_rate)
        net       = ebit - tax
        contrib   = self.price - self.var_cost
        be_qty    = safe_div(self.fixed_monthly, contrib, float("inf")) if contrib > 0 else float("inf")
        roi       = safe_div(net, self.capex_init) * 100
        gp_mg     = safe_div(gp, rev)
        ebitda_mg = safe_div(ebitda, rev)
        net_mg    = safe_div(net, rev)
        util      = safe_div(self.qty, be_qty) if be_qty not in (float("inf"), 0) else 0.0

        # Composite health score 0–100
        s_margin = min(100, max(0, net_mg * 400))
        s_roi    = min(100, max(0, roi * 5))
        s_util   = min(100, max(0, util * 80))
        health   = int(s_margin * 0.40 + s_roi * 0.30 + s_util * 0.30)

        return dict(
            rev=rev, vc_tot=vc_tot, gp=gp, fc_tot=fc_tot,
            ebitda=ebitda, depr=depr, ebit=ebit, tax=tax, net=net,
            contrib=contrib, be_qty=be_qty, roi=roi,
            gp_mg=gp_mg, ebitda_mg=ebitda_mg, net_mg=net_mg,
            util=util, health=health,
        )

    # =========================================================================
    # 1 — Hero banner
    # =========================================================================

    def _hero_banner(self, f: dict) -> None:
        h = f["health"]
        if h >= 70:
            col, status, bg_orb, status_bg = (
                "#34D399", "✅ Healthy",
                "rgba(52,211,153,0.18)", "rgba(52,211,153,0.18)"
            )
        elif h >= 40:
            col, status, bg_orb, status_bg = (
                _AMBER, "⚠️ Caution",
                "rgba(245,158,11,0.18)", "rgba(245,158,11,0.18)"
            )
        else:
            col, status, bg_orb, status_bg = (
                _RED, "🔴 At Risk",
                "rgba(244,63,94,0.18)", "rgba(244,63,94,0.18)"
            )

        badges = [
            f"💰 Revenue {fmt(f['rev'])}",
            f"📊 Net Margin {f['net_mg']:.1%}",
            f"⚡ EBITDA Margin {f['ebitda_mg']:.1%}",
            f"📈 ROI {f['roi']:.1f}%",
            f"🏆 GP Margin {f['gp_mg']:.1%}",
        ]
        badges_html = "".join(
            f"<span class='fnx-hero-badge'>{b}</span>" for b in badges
        )

        st.markdown(f"""
        <div class="fnx-hero">
          <div class="fnx-hero-topline"></div>
          <div class="fnx-hero-left">
            <h2>Business Health Overview</h2>
            <p>Annualised figures &nbsp;·&nbsp; powered by sidebar financial parameters</p>
            <div class="fnx-badge-row">{badges_html}</div>
          </div>
          <div class="fnx-health">
            <div class="fnx-health-orb" style="
                background:{bg_orb};
                border: 2px solid {col}55;
                --orb-glow-a: 0 0 0 4px {col}22, 0 0 28px {col}30, inset 0 0 18px {col}15;
                --orb-glow-b: 0 0 0 8px {col}15, 0 0 48px {col}40, inset 0 0 24px {col}20;">
              <div class="score" style="color:{col}">{h}</div>
              <div class="slash" style="color:{col}80">/ 100</div>
            </div>
            <div class="label">Health Score</div>
            <div class="status-badge" style="
                background:{status_bg};
                color:{col};
                border: 1px solid {col}45">{status}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # Section header helper
    # =========================================================================

    def _section(self, icon: str, bg: str, title: str, sub: str) -> None:
        st.markdown(f"""
        <div class="fnx-section" style="--sec-color:{bg}">
          <div class="fnx-section-icon" style="background:{bg}1F">{icon}</div>
          <div class="fnx-section-text">
            <h3>{title}</h3>
            <p>{sub}</p>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # 2 — KPI Cards
    # =========================================================================

    def _kpi_cards(self, f: dict) -> None:
        be_str   = f'{f["be_qty"]:,.0f} units/mo' if f["be_qty"] != float("inf") else "∞"
        util_str = f'{f["util"]:.1%} of BEP'      if f["be_qty"] != float("inf") else "N/A"
        nm_cls   = "pos" if f["net_mg"] > 0.10 else ("neu" if f["net_mg"] > 0 else "neg")
        roi_cls  = "pos" if f["roi"] > 15 else ("neu" if f["roi"] > 0 else "neg")
        util_cls = "pos" if f["util"] >= 1.2 else ("neu" if f["util"] >= 1.0 else "neg")

        cards = [
            ("c-teal",   "💰", "Annual Revenue",  fmt(f["rev"]),      f"GP {f['gp_mg']:.1%}",         "pos"),
            ("c-navy",   "📊", "Gross Profit",    fmt(f["gp"]),       f"Margin {f['gp_mg']:.1%}",      "pos" if f["gp"] > 0 else "neg"),
            ("c-amber",  "⚡", "EBITDA",          fmt(f["ebitda"]),   f"Margin {f['ebitda_mg']:.1%}",  "pos" if f["ebitda"] > 0 else "neg"),
            ("c-green",  "🏆", "Net Profit",      fmt(f["net"]),      f"Margin {f['net_mg']:.1%}",     nm_cls),
            ("c-red",    "📏", "Breakeven",       be_str,             util_str,                         util_cls),
            ("c-purple", "📈", "CapEx ROI",       f'{f["roi"]:.1f}%', f"On {fmt(self.capex_init)}",    roi_cls),
        ]
        html = "<div class='fnx-kpi-grid'>"
        for cls, ghost, lbl, val, delta, dcls in cards:
            html += f"""
            <div class="fnx-kpi {cls}">
              <div class="fnx-kpi-icon">{ghost}</div>
              <div class="fnx-kpi-lbl">{lbl}</div>
              <div class="fnx-kpi-val">{val}</div>
              <div class="fnx-kpi-sub">
                <span class="fnx-delta {dcls}">{delta}</span>
              </div>
              <div class="fnx-kpi-ghost">{ghost}</div>
            </div>"""
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # =========================================================================
    # 3 — Revenue Intelligence (Area + Line combo, dual axis)
    # =========================================================================

    def _revenue_intelligence(self, f: dict) -> None:
        rows: list[dict] = []
        for i in range(self.forecast_years):
            rev  = f["rev"]    * (1 + self.rev_growth)   ** i
            vc   = f["vc_tot"] * (1 + self.vc_inflation)  ** i
            fc   = f["fc_tot"] * (1 + self.fc_inflation)  ** i
            ebit = rev - vc - fc - f["depr"]
            tax  = max(0.0, ebit * self.tax_rate)
            net  = ebit - tax
            rows.append({
                "Year":        f"Yr {i+1}",
                "Revenue":     rev,
                "Total Costs": vc + fc + f["depr"],
                "Net Profit":  net,
                "Net Margin":  safe_div(net, rev) * 100,
                "GP Margin":   safe_div(rev - vc, rev) * 100,
                "EBITDA Margin": safe_div(rev - vc - fc, rev) * 100,
            })
        df = pd.DataFrame(rows)

        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
        )

        # Revenue filled area (gradient-like via fillgradient)
        fig.add_trace(go.Scatter(
            x=df["Year"], y=df["Revenue"], name="Revenue",
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(0,194,178,0.10)",
            line=dict(color=_TEAL, width=3),
            hovertemplate="<b>%{x}</b><br>Revenue: " + _CUR + "%{y:,.0f}<extra></extra>",
        ), secondary_y=False)

        # Costs filled area
        fig.add_trace(go.Scatter(
            x=df["Year"], y=df["Total Costs"], name="Total Costs",
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(244,63,94,0.07)",
            line=dict(color=_RED, width=2, dash="dot"),
            hovertemplate="<b>%{x}</b><br>Costs: " + _CUR + "%{y:,.0f}<extra></extra>",
        ), secondary_y=False)

        # Net Profit bars
        bar_colors = [_GREEN if v >= 0 else _RED for v in df["Net Profit"]]
        fig.add_trace(go.Bar(
            x=df["Year"], y=df["Net Profit"], name="Net Profit",
            marker=dict(color=bar_colors, opacity=0.75, line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>Net Profit: " + _CUR + "%{y:,.0f}<extra></extra>",
        ), secondary_y=False)

        # Net Margin line (secondary axis) — glow
        fig.add_trace(go.Scatter(
            x=df["Year"], y=df["Net Margin"],
            mode="lines", name="_glow", showlegend=False,
            line=dict(color=_AMBER, width=8), opacity=0.15,
            hoverinfo="skip",
        ), secondary_y=True)
        fig.add_trace(go.Scatter(
            x=df["Year"], y=df["Net Margin"], name="Net Margin %",
            mode="lines+markers",
            line=dict(color=_AMBER, width=2.5),
            marker=dict(size=8, color=_AMBER,
                        line=dict(color="#fff", width=2)),
            hovertemplate="<b>%{x}</b><br>Net Margin: %{y:.1f}%<extra></extra>",
        ), secondary_y=True)

        # GP Margin line (secondary axis)
        fig.add_trace(go.Scatter(
            x=df["Year"], y=df["GP Margin"], name="GP Margin %",
            mode="lines+markers",
            line=dict(color=_BLUE, width=2, dash="dash"),
            marker=dict(size=6, color=_BLUE,
                        line=dict(color="#fff", width=2)),
            hovertemplate="<b>%{x}</b><br>GP Margin: %{y:.1f}%<extra></extra>",
        ), secondary_y=True)

        fig.update_layout(
            **_BASE,
            title=dict(
                text=f"<b>Revenue vs Costs vs Margins</b> — {self.forecast_years}-Year Projection",
                font=dict(size=15, color=_NAVY, family="'Syne',sans-serif"),
                x=0,
            ),
            barmode="overlay",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1,
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#E5E7EB",
                borderwidth=1,
            ),
            yaxis=dict(
                title=f"Amount ({_CUR})",
                gridcolor="#F1F5F9",
                tickformat=",.0f",
                tickprefix=_CUR,
                tickfont=dict(size=11),
                zeroline=True,
                zerolinecolor="#E2E8F0",
                zerolinewidth=1,
            ),
            yaxis2=dict(
                title="Margin (%)",
                ticksuffix="%",
                gridcolor="rgba(0,0,0,0)",
                range=[-5, max(df["GP Margin"].max() * 1.25, 10)],
                tickfont=dict(size=11),
            ),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # 4a — Monthly Waterfall
    # =========================================================================

    def _waterfall(self, f: dict) -> None:
        rev   = self.price * self.qty
        vc    = self.var_cost * self.qty
        fc    = self.fixed_monthly
        depr  = f["depr"] / 12
        pbt   = rev - vc - fc
        tax   = max(0.0, pbt * self.tax_rate)
        net   = pbt - tax

        measures = ["absolute", "relative", "relative", "relative", "relative", "total"]
        x_labels = ["Revenue", "Variable Costs", "Fixed Costs", "Gross Profit → EBIT", "Tax", "Net Profit"]
        y_vals   = [rev, -vc, -fc, -depr, -tax, net]

        color_map = {
            "absolute": "#00C2B2",
            "relative": None,
            "total":    "#0B1F3A",
        }

        fig = go.Figure(go.Waterfall(
            orientation = "v",
            measure     = measures,
            x           = x_labels,
            y           = y_vals,
            text        = [fmt(abs(v)) for v in y_vals],
            textposition= "outside",
            textfont    = dict(family="'DM Sans','Plus Jakarta Sans',sans-serif", size=11, color=_NAVY),
            connector   = dict(line=dict(color="#D1D5DB", width=1.5, dash="dot")),
            increasing  = dict(marker=dict(color=_TEAL)),
            decreasing  = dict(marker=dict(color=_RED)),
            totals      = dict(marker=dict(color=_NAVY)),
            opacity     = 0.85,
        ))
        fig.update_layout(
            **_BASE,
            title=dict(
                text="<b>Monthly P&L Waterfall</b>",
                font=dict(size=15, color=_NAVY, family="'Syne',sans-serif"), x=0,
            ),
            yaxis=dict(
                tickprefix=_CUR, tickformat=",.0f",
                gridcolor="#F1F5F9",
                tickfont=dict(size=11),
                zeroline=True, zerolinecolor="#E2E8F0",
            ),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # 4b — Cost Structure Donut (replaces old sunburst)
    # =========================================================================

    def _cost_donut(self, f: dict) -> None:
        vc   = f["vc_tot"]
        fc   = f["fc_tot"]
        depr = f["depr"]
        tax  = max(0.0, f["tax"])
        net  = max(0.0, f["net"])

        labels = ["Variable Costs", "Fixed Costs", "Depreciation", "Tax", "Net Profit"]
        values = [max(0, vc), max(0, fc), max(0, depr), max(0, tax), net]
        colors = [_RED, _AMBER, _SLATE, "#475569", _TEAL]

        fig = go.Figure(go.Pie(
            labels       = labels,
            values       = values,
            hole         = 0.62,
            marker       = dict(colors=colors, line=dict(color="#fff", width=3)),
            textfont     = dict(family="'DM Sans','Plus Jakarta Sans',sans-serif", size=11),
            hovertemplate= "<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>",
            customdata   = [fmt(v) for v in values],
            textposition = "outside",
            textinfo     = "percent",
            pull         = [0, 0, 0, 0, 0.04],
        ))
        fig.add_annotation(
            text=f"<b style='font-size:16px;color:{_NAVY}'>Revenue<br>Split</b>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="'DM Sans','Plus Jakarta Sans',sans-serif", size=13, color=_NAVY),
        )
        fig.update_layout(
            **_BASE,
            title=dict(
                text="<b>Annual Cost Structure</b>",
                font=dict(size=15, color=_NAVY, family="'Syne',sans-serif"), x=0,
            ),
            legend=dict(
                orientation="v",
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.8)",
            ),
            height=370,
        )
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # 5 — Breakeven Analysis
    # =========================================================================

    def _breakeven(self, f: dict) -> None:
        contrib = f["contrib"]
        be_qty  = f["be_qty"]
        if contrib <= 0 or be_qty == float("inf"):
            st.info("⚠️ Contribution margin ≤ 0 — adjust price / variable cost to enable breakeven analysis.")
            return

        # BEP mini-metrics strip
        margin_of_safety = max(0.0, (self.qty - be_qty) / self.qty) if self.qty > 0 else 0.0
        bep_rev = be_qty * self.price
        st.markdown(f"""
        <div class='fnx-bep-row'>
          <div class='fnx-bep-cell'>
            <div class='bv'>{be_qty:,.0f}</div>
            <div class='bl'>BEP (units/mo)</div>
          </div>
          <div class='fnx-bep-cell'>
            <div class='bv'>{fmt(bep_rev)}</div>
            <div class='bl'>BEP Revenue</div>
          </div>
          <div class='fnx-bep-cell'>
            <div class='bv'>{fmt(contrib)}</div>
            <div class='bl'>Contribution/Unit</div>
          </div>
          <div class='fnx-bep-cell'>
            <div class='bv'>{margin_of_safety:.1%}</div>
            <div class='bl'>Margin of Safety</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Chart
        max_q  = max(be_qty * 2.0, self.qty * 1.5, 100)
        x      = np.linspace(0, max_q, 300)
        rev_l  = x * self.price
        tc_l   = self.fixed_monthly + x * self.var_cost
        profit = rev_l - tc_l

        fig = go.Figure()

        # Profit zone shading
        fig.add_trace(go.Scatter(
            x=np.append(x[x >= be_qty], x[x >= be_qty][::-1]),
            y=np.append(profit[x >= be_qty], rev_l[x >= be_qty][::-1] * 0 + self.fixed_monthly + be_qty * self.var_cost),
            fill="toself",
            fillcolor="rgba(16,185,129,0.07)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Loss zone shading
        fig.add_trace(go.Scatter(
            x=np.append(x[x < be_qty], x[x < be_qty][::-1]),
            y=np.append(profit[x < be_qty], np.zeros(len(x[x < be_qty]))),
            fill="toself",
            fillcolor="rgba(244,63,94,0.05)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Revenue line
        fig.add_trace(go.Scatter(
            x=x, y=rev_l, name="Revenue",
            mode="lines",
            line=dict(color=_TEAL, width=2.5),
            hovertemplate="Units: %{x:,.0f}<br>Revenue: " + _CUR + "%{y:,.0f}<extra></extra>",
        ))

        # Total cost line
        fig.add_trace(go.Scatter(
            x=x, y=tc_l, name="Total Costs",
            mode="lines",
            line=dict(color=_RED, width=2, dash="dash"),
            hovertemplate="Units: %{x:,.0f}<br>Costs: " + _CUR + "%{y:,.0f}<extra></extra>",
        ))

        # Fixed costs baseline
        fig.add_trace(go.Scatter(
            x=x, y=np.full_like(x, self.fixed_monthly), name="Fixed Costs",
            mode="lines",
            line=dict(color=_SLATE, width=1.5, dash="dot"),
            opacity=0.6,
            hoverinfo="skip",
        ))

        # BEP vertical line
        fig.add_shape(
            type="line",
            x0=be_qty, x1=be_qty, y0=0, y1=bep_rev * 1.05,
            line=dict(color=_AMBER, width=2, dash="dash"),
        )

        # Current volume marker
        curr_rev = self.qty * self.price
        fig.add_trace(go.Scatter(
            x=[self.qty], y=[curr_rev], name=f"Current ({self.qty:,.0f} units)",
            mode="markers",
            marker=dict(size=12, color=_BLUE, symbol="diamond",
                        line=dict(color="#fff", width=2)),
            hovertemplate="Current Volume<br>Units: %{x:,.0f}<br>Revenue: " + _CUR + "%{y:,.0f}<extra></extra>",
        ))

        fig.add_annotation(
            x=be_qty, y=bep_rev * 1.06,
            text=f"<b>BEP: {be_qty:,.0f} units</b>",
            showarrow=True,
            arrowhead=2, arrowsize=1, arrowcolor=_AMBER,
            font=dict(size=11, color=_AMBER, family="'DM Sans','Plus Jakarta Sans',sans-serif"),
            bgcolor="#FFFBEB", bordercolor=_AMBER, borderwidth=1,
        )

        fig.update_layout(
            **_BASE,
            title=dict(
                text="<b>Breakeven Analysis</b> — Revenue vs Total Costs",
                font=dict(size=15, color=_NAVY, family="'Syne',sans-serif"), x=0,
            ),
            xaxis=dict(title="Monthly Units Sold", gridcolor="#F1F5F9", tickfont=dict(size=11)),
            yaxis=dict(title=f"Amount ({_CUR})", tickprefix=_CUR,
                       tickformat=",.0f", gridcolor="#F1F5F9", tickfont=dict(size=11),
                       zeroline=True, zerolinecolor="#E2E8F0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=11),
                        bgcolor="rgba(255,255,255,0.85)",
                        bordercolor="#E5E7EB", borderwidth=1),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # 6 — Margin trend heatmap
    # =========================================================================

    def _margin_heatmap(self, f: dict) -> None:
        metrics = ["Revenue", "GP Margin", "EBITDA Margin", "Net Margin", "Net Profit"]
        rows = []
        prev = None
        for i in range(self.forecast_years):
            rev  = f["rev"]    * (1 + self.rev_growth)   ** i
            vc   = f["vc_tot"] * (1 + self.vc_inflation)  ** i
            fc   = f["fc_tot"] * (1 + self.fc_inflation)  ** i
            ebt  = rev - vc - fc - f["depr"]
            net  = ebt - max(0.0, ebt * self.tax_rate)
            curr = {
                "Revenue":      rev,
                "GP Margin":    safe_div(rev - vc, rev) * 100,
                "EBITDA Margin": safe_div(rev - vc - fc, rev) * 100,
                "Net Margin":   safe_div(net, rev) * 100,
                "Net Profit":   net,
            }
            if prev:
                row = {m: safe_div(curr[m] - prev[m], abs(prev[m])) * 100 for m in metrics}
            else:
                row = {m: 0.0 for m in metrics}
            row["Year"] = f"Yr {i+1}"
            rows.append(row)
            prev = curr

        df = pd.DataFrame(rows).set_index("Year")
        z  = df[metrics].values
        fig = go.Figure(go.Heatmap(
            z           = z,
            x           = metrics,
            y           = df.index.tolist(),
            colorscale  = [[0, "#F43F5E"], [0.5, "#F9FAFB"], [1, "#10B981"]],
            zmid        = 0,
            text        = [[f"{v:.1f}%" for v in row] for row in z],
            texttemplate= "%{text}",
            textfont    = dict(size=12, family="'DM Sans','Plus Jakarta Sans',sans-serif"),
            hovertemplate= "<b>%{y} — %{x}</b><br>YoY Change: %{z:.2f}%<extra></extra>",
            colorbar     = dict(
                title=dict(text="YoY %", font=dict(size=11)),
                tickformat=".0f",
                ticksuffix="%",
                len=0.8,
            ),
        ))
        fig.update_layout(
            **_BASE,
            title=dict(
                text="<b>Year-over-Year Growth Heatmap</b>",
                font=dict(size=15, color=_NAVY, family="'Syne',sans-serif"), x=0,
            ),
            xaxis=dict(side="bottom", tickfont=dict(size=11)),
            yaxis=dict(tickfont=dict(size=11)),
            height=max(180, self.forecast_years * 56 + 110),
        )
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # 7 — AI insights
    # =========================================================================

    def _insights(self, f: dict) -> None:
        self._insight_box(
            what=(
                f"Annual revenue of {fmt(f['rev'])} with a net margin of "
                f"{f['net_mg']:.1%} and EBITDA margin of {f['ebitda_mg']:.1%}. "
                f"Breakeven at {f['be_qty']:,.0f} units/month against current "
                f"volume of {self.qty:,.0f} units."
            ),
            recommendation=(
                "Focus on unit economics — raising the contribution margin "
                f"(currently {fmt(f['contrib'])}/unit) by 10% has a compounded "
                "effect on all downstream margins. "
                "Monitor fixed-cost inflation closely over the projection period."
            ),
            context_data={
                "Annual Revenue":     fmt(f["rev"]),
                "Gross Profit":       fmt(f["gp"]),
                "EBITDA":             fmt(f["ebitda"]),
                "Net Profit":         fmt(f["net"]),
                "GP Margin":          f"{f['gp_mg']:.1%}",
                "EBITDA Margin":      f"{f['ebitda_mg']:.1%}",
                "Net Margin":         f"{f['net_mg']:.1%}",
                "CapEx ROI":          f"{f['roi']:.1f}%",
                "Health Score":       f"{f['health']}/100",
                "Contribution/Unit":  fmt(f["contrib"]),
            },
        )