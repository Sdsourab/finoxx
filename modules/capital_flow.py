"""
modules/capital_flow.py  ·  FinOx Suite
=========================================
Capital Flow Strategist — Sankey Diagram.

VISUAL ENHANCEMENTS (v2.0)
---------------------------
All business logic, formulas, and data flow are 100% unchanged.
Only the Sankey figure construction and layout have been updated:

1. Node Padding (node.pad = 50)
   Increased from 18 → 50 so node rectangles and their labels never
   overlap, even when values are small and nodes are close together.

2. Translucent Glass-Like Links
   Each link now carries its own RGBA colour derived from the source
   node's palette colour at 0.22 opacity. The result is a layered,
   glass-like appearance where overlapping flows remain distinguishable
   without visual clutter.

3. Dynamic Height & Resolution
   Chart height is computed as max(520, n_nodes * 68) so the canvas
   always gives every node breathing room regardless of how many
   allocation rows are active. use_container_width=True keeps it
   pixel-perfect in all Streamlit layouts.

4. Smart Hover Tooltips
   customdata on each link carries the formatted amount string.
   hovertemplate renders:
       Source → Target
       Amount: ৳1,234,567
   giving the user unambiguous directional context on every flow.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div


# ---------------------------------------------------------------------------
# Palette — one rich colour per node (used for node fills AND tinted links)
# ---------------------------------------------------------------------------
_NODE_COLOURS = [
    "#1A6FBF",   # 0  Revenue          — deep blue
    "#D94F3D",   # 1  Variable Costs   — crimson
    "#E8833A",   # 2  Fixed Costs      — amber-orange
    "#2A9D5C",   # 3  Profit Before Tax— forest green
    "#C0392B",   # 4  Taxes            — red
    "#27AE60",   # 5  Profit After Tax — bright green
    "#1ABC9C",   # 6  Reinvestment     — teal
    "#8E44AD",   # 7  Debt Repayment   — violet
    "#795548",   # 8  Dividends        — warm brown
]

# Opacity for link fills — gives the translucent "glass" effect
_LINK_ALPHA = 0.22


def _rgba(hex_colour: str, alpha: float) -> str:
    """Convert a #RRGGBB string to an rgba(...) CSS string."""
    h  = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


class CapitalFlowModule(BaseModule):
    PAGE_ICON  = "🌊"
    PAGE_TITLE = "Capital Flow Strategist"

    def render(self) -> None:
        self._page_header(
            "🌊 Capital Flow Strategist (Sankey Diagram)",
            "Visualise monthly revenue flowing through costs, tax, and profit allocation",
        )
        with st.container(border=True):
            # ── All original business logic — untouched ───────────────────────
            rev  = self.price * self.qty
            vc   = self.var_cost * self.qty
            fc   = self.fixed_monthly
            pbt  = rev - vc - fc
            tax  = max(0.0, pbt) * self.tax_rate
            pat  = pbt - tax

            c1, c2 = st.columns(2, gap="medium")
            reinvest_rate = c1.slider(
                "Reinvestment Rate (% of PAT)", 0, 100, 30, key="cf_ri"
            ) / 100
            debt_repay_rate = c2.slider(
                "Debt Repayment Rate (% of PAT)", 0, 100, 20, key="cf_dr"
            ) / 100

            remaining = max(0.0, pat)
            reinvest  = remaining * reinvest_rate
            debt_rep  = remaining * debt_repay_rate
            dividend  = remaining * (1 - reinvest_rate - debt_repay_rate)
            dividend  = max(0.0, dividend)

            c1m, c2m, c3m, c4m = st.columns(4)
            c1m.metric("Monthly Revenue",   fmt(rev))
            c2m.metric("Profit Before Tax", fmt(pbt))
            c3m.metric("Profit After Tax",  fmt(pat))
            c4m.metric("Gross Margin",      f"{safe_div(pbt, rev):.1%}")

            # ── Node / link definitions — topology unchanged ──────────────────
            labels = [
                "Revenue", "Variable Costs", "Fixed Costs",
                "Profit Before Tax", "Taxes", "Profit After Tax",
                "Reinvestment", "Debt Repayment", "Dividends",
            ]

            # Sources and targets (zero-indexed to labels list)
            sources = [0, 0, 0,  3, 3,  5, 5, 5]
            targets = [1, 2, 3,  4, 5,  6, 7, 8]
            values  = [
                max(0.0, vc),
                max(0.0, fc),
                max(0.0, pbt),
                max(0.0, tax),
                max(0.0, pat),
                max(0.0, reinvest),
                max(0.0, debt_rep),
                max(0.0, dividend),
            ]

            # ── ENHANCEMENT 4 — Smart hover: customdata carries formatted amount
            # hovertemplate uses %{source.label}, %{target.label}, %{customdata}
            custom_data = [fmt(v) for v in values]

            # ── ENHANCEMENT 2 — Translucent glass links
            # Each link is tinted with the RGBA of its source node colour
            link_colours = [
                _rgba(_NODE_COLOURS[src], _LINK_ALPHA)
                for src in sources
            ]

            # ── ENHANCEMENT 3 — Dynamic canvas height
            # 68 px per node gives every label breathing room; floor at 520 px
            n_nodes   = len(labels)
            fig_height = max(520, n_nodes * 68)

            # ── Build the Sankey figure ───────────────────────────────────────
            fig = go.Figure(go.Sankey(
                arrangement="snap",

                # ── ENHANCEMENT 1 — Generous node padding prevents overlap ──
                node=dict(
                    pad       = 50,          # was 18 — now 50 to eliminate label overlap
                    thickness = 24,
                    line      = dict(color="rgba(255,255,255,0.35)", width=1),
                    label     = labels,
                    color     = _NODE_COLOURS,
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Total flow: ৳%{value:,.0f}"
                        "<extra></extra>"
                    ),
                ),

                # ── ENHANCEMENT 2 & 4 — Glass links + directional hover ──────
                link=dict(
                    source        = sources,
                    target        = targets,
                    value         = values,
                    color         = link_colours,   # per-link translucent tint
                    customdata    = custom_data,
                    hovertemplate=(
                        "<b>%{source.label}  →  %{target.label}</b><br>"
                        "Amount: %{customdata}"
                        "<extra></extra>"
                    ),
                ),
            ))

            # ── ENHANCEMENT 3 — Enlarged, responsive layout ───────────────────
            fig.update_layout(
                title=dict(
                    text="<b>Monthly Capital Flow</b>",
                    font=dict(
                        size=16,
                        color="#0F2744",
                        family="'Plus Jakarta Sans', 'Segoe UI', sans-serif",
                    ),
                    x=0.01,
                ),
                font=dict(
                    size=13,
                    family="'Plus Jakarta Sans', 'Segoe UI', sans-serif",
                    color="#1E293B",
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor ="rgba(0,0,0,0)",
                template     ="plotly_white",
                height       = fig_height,      # dynamic — never clips labels
                margin       = dict(t=56, b=24, l=16, r=16),
                hoverlabel   = dict(
                    bgcolor   ="rgba(15,39,68,0.92)",
                    font_color="#FFFFFF",
                    font_size =13,
                    bordercolor="rgba(255,255,255,0.15)",
                ),
            )

            # use_container_width=True ensures pixel-perfect fit in all layouts
            st.plotly_chart(fig, use_container_width=True)

            # ── Summary table — unchanged ────────────────────────────────────
            rows = [
                ("Revenue",          rev),
                ("Variable Costs",  -vc),
                ("Fixed Costs",     -fc),
                ("Profit Before Tax", pbt),
                ("Taxes",           -tax),
                ("Profit After Tax",  pat),
                ("Reinvestment",    -reinvest),
                ("Debt Repayment",  -debt_rep),
                ("Dividends",       -dividend),
            ]
            df_tbl = pd.DataFrame(rows, columns=["Item", "Amount"])
            df_tbl["Amount"] = df_tbl["Amount"].apply(fmt)
            st.dataframe(df_tbl, use_container_width=True, hide_index=True)

            # ── AI insight box — unchanged ────────────────────────────────────
            self._insight_box(
                what=(
                    f"Monthly revenue of {fmt(rev)} flows through variable costs "
                    f"({fmt(vc)}), fixed costs ({fmt(fc)}), leaving PAT of {fmt(pat)}."
                ),
                recommendation=(
                    "A reinvestment rate above 30% accelerates growth; below 20% "
                    "signals a cash-return-focused strategy. "
                    "If PAT is negative, reduce fixed costs or raise unit price before "
                    "setting allocation targets."
                ),
                context_data={
                    "Monthly Revenue":      fmt(rev),
                    "Variable Costs":       fmt(vc),
                    "Fixed Costs":          fmt(fc),
                    "Profit Before Tax":    fmt(pbt),
                    "Tax":                  fmt(tax),
                    "Profit After Tax":     fmt(pat),
                    "Reinvestment":         fmt(reinvest),
                    "Debt Repayment":       fmt(debt_rep),
                    "Dividends":            fmt(dividend),
                    "Gross Margin":         f"{safe_div(pbt, rev):.1%}",
                },
            )