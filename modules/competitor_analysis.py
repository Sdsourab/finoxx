"""
modules/competitor_analysis.py  ·  FinOx Suite
================================================
Competitor Analysis & Market Positioning.

FIX (v2.1) — AttributeError: 'list' object has no attribute 'items'
----------------------------------------------------------------------
BEFORE:
    context_data=df.to_dict(orient="records")

    Returns a LIST of dicts → _build_enriched_context crashes on .items().

FIX:
    Build a proper flat dict with summary KPIs + per-competitor detail rows.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt


class CompetitorAnalysisModule(BaseModule):
    PAGE_ICON  = "🎯"
    PAGE_TITLE = "Competitor Analysis"

    _SAMPLE = pd.DataFrame({
        "Competitor":      ["Our Company", "Competitor A", "Competitor B", "Competitor C"],
        "Price_Index":     [100, 90, 120, 110],
        "Quality_Score":   [9.0, 7.0, 8.0, 9.5],
        "Market_Share":    [0.25, 0.30, 0.20, 0.15],
        "Innovation":      [8.0, 6.0, 9.0, 7.5],
        "Service_Score":   [8.5, 7.5, 7.0, 9.0],
    })

    def render(self) -> None:
        self._page_header(
            "🎯 Competitor Analysis & Market Positioning",
            "Edit the table to update the positioning map and radar chart in real time",
        )
        with st.container(border=True):
            df = st.data_editor(
                self._SAMPLE, num_rows="dynamic", height=220, key="comp_ed"
            )
            if df.empty:
                self._info_box("Add at least one competitor to begin analysis.")
                return

            tab1, tab2 = st.tabs(["📍 Positioning Map", "🕸️ Radar Chart"])

            with tab1:
                fig = px.scatter(
                    df, x="Price_Index", y="Quality_Score",
                    size="Market_Share", color="Competitor",
                    text="Competitor", size_max=100,
                    title="Price vs Quality — bubble size = Market Share",
                    hover_data={"Market_Share": ":.0%"},
                    template="plotly_white",
                )
                fig.add_hline(
                    y=df["Quality_Score"].mean(),
                    line_dash="dot", line_color="grey",
                    annotation_text=f"Avg Quality {df['Quality_Score'].mean():.1f}",
                )
                fig.add_vline(
                    x=df["Price_Index"].mean(),
                    line_dash="dot", line_color="grey",
                    annotation_text=f"Avg Price {df['Price_Index'].mean():.0f}",
                )
                fig.update_traces(textposition="top center")
                st.plotly_chart(fig, use_container_width=True)

                top_ms = df.loc[df["Market_Share"].idxmax(), "Competitor"]
                top_qs = df.loc[df["Quality_Score"].idxmax(), "Competitor"]

                # ── FIX: flat dict instead of df.to_dict(orient="records") ──────
                context_dict: dict = {
                    "Total Competitors":        len(df),
                    "Market Share Leader":       top_ms,
                    "Market Share (Leader)":     f"{df['Market_Share'].max():.0%}",
                    "Quality Score Leader":      top_qs,
                    "Quality Score (Leader)":    f"{df['Quality_Score'].max():.1f}/10",
                    "Avg Price Index":           f"{df['Price_Index'].mean():.0f}",
                    "Avg Quality Score":         f"{df['Quality_Score'].mean():.1f}",
                    "Total Market Share Tracked": f"{df['Market_Share'].sum():.0%}",
                }
                # Per-competitor rows as flat entries
                for _, row in df.iterrows():
                    key = f"Competitor — {row['Competitor']}"
                    context_dict[key] = (
                        f"Market Share: {row['Market_Share']:.0%} | "
                        f"Price Index: {row['Price_Index']:.0f} | "
                        f"Quality: {row['Quality_Score']:.1f} | "
                        f"Innovation: {row.get('Innovation', 'N/A')} | "
                        f"Service: {row.get('Service_Score', 'N/A')}"
                    )

                self._insight_box(
                    what=(
                        f"Market share leader: **{top_ms}** ({df['Market_Share'].max():.0%}). "
                        f"Quality leader: **{top_qs}** ({df['Quality_Score'].max():.1f}/10). "
                        f"Average Price Index: {df['Price_Index'].mean():.0f}."
                    ),
                    recommendation=(
                        f"**{top_ms}** leads on market share — study their pricing "
                        "and distribution. If quality score is below average, invest in "
                        "product improvements before attempting a price increase."
                    ),
                    context_data=context_dict,
                )

            with tab2:
                attrs = ["Quality_Score", "Innovation", "Service_Score"]
                avail = [c for c in attrs if c in df.columns]
                if len(avail) < 3:
                    self._info_box("Ensure all three columns exist: Quality_Score, Innovation, Service_Score.")
                    return
                fig2 = go.Figure()
                for _, row in df.iterrows():
                    vals = [row[c] for c in avail] + [row[avail[0]]]
                    fig2.add_trace(go.Scatterpolar(
                        r=vals, theta=avail + [avail[0]],
                        fill="toself", name=str(row["Competitor"]),
                    ))
                fig2.update_layout(
                    polar=dict(radialaxis=dict(range=[0, 10])),
                    title="Multi-Attribute Competitive Radar",
                    template="plotly_white",
                )
                st.plotly_chart(fig2, use_container_width=True)