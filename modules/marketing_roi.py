"""
modules/marketing_roi.py  ·  FinOx Suite
==========================================
Advanced Marketing Intelligence Suite.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div


class MarketingROIModule(BaseModule):
    PAGE_ICON  = "📢"
    PAGE_TITLE = "Marketing ROI"

    _SAMPLE = pd.DataFrame({
        "Campaign":         ["Google Ads Q1", "Facebook Ads Q1", "Email Marketing Q2", "Content Marketing Q2"],
        "Spend":            [75_000, 50_000, 25_000, 40_000],
        "Impressions":      [1_000_000, 1_200_000, 500_000, 800_000],
        "Clicks":           [10_000, 15_000, 20_000, 12_000],
        "Leads":            [550, 400, 1_000, 300],
        "Conversion_Rate":  [0.08, 0.05, 0.04, 0.10],
    })

    def render(self) -> None:
        self._page_header(
            "📢 Advanced Marketing Intelligence Suite",
            "Edit campaign data · adjust LTV · optimise budget allocation",
        )
        with st.container(border=True):
            df = st.data_editor(
                self._SAMPLE, num_rows="dynamic", height=200, key="mkt_ed"
            )
            c1, c2 = st.columns(2)
            lt = c1.slider("Customer Lifetime (months)", 1, 60, 12, key="mkt_lt")
            rr = c2.slider("Monthly Repeat Purchase %",  0, 100, 20, key="mkt_rr") / 100

            if df.empty:
                self._info_box("Add at least one campaign row to begin.")
                return

            gp = self.price - self.var_cost
            df = df.copy()
            df["CTR"]           = df.apply(lambda r: safe_div(r["Clicks"],       r["Impressions"]), axis=1)
            df["CPC"]           = df.apply(lambda r: safe_div(r["Spend"],        r["Clicks"]),       axis=1)
            df["New_Customers"] = df["Leads"] * df["Conversion_Rate"]
            df["CAC"]           = df.apply(lambda r: safe_div(r["Spend"], r["New_Customers"]),       axis=1)
            df["LTV"]           = gp * (1 + lt * rr)
            df["Total_GP"]      = df["New_Customers"] * df["LTV"]
            df["Net_Profit"]    = df["Total_GP"] - df["Spend"]
            df["ROI"]           = df.apply(lambda r: safe_div(r["Net_Profit"], r["Spend"]),          axis=1)
            df["LTV_CAC"]       = df.apply(lambda r: safe_div(r["LTV"],        r["CAC"]),             axis=1)
            df = df.fillna(0.0)

            tab1, tab2, tab3 = st.tabs([
                "📊 Campaign Performance", "📈 LTV vs CAC", "⚙️ Budget Optimizer"
            ])

            with tab1:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df["Campaign"], y=df["Total_GP"], name="Gross Profit",
                    marker_color="#00b4d8",
                ))
                fig.add_trace(go.Bar(
                    x=df["Campaign"], y=df["Spend"], name="Spend",
                    marker_color="#d62728",
                ))
                fig.add_trace(go.Scatter(
                    x=df["Campaign"], y=df["ROI"],
                    mode="lines+markers+text", name="ROI",
                    yaxis="y2",
                    text=[f"{r:.1%}" for r in df["ROI"]],
                    textposition="top center",
                    line=dict(color="#ff7f0e", width=2),
                ))
                fig.update_layout(
                    barmode="group",
                    yaxis2=dict(overlaying="y", side="right", tickformat=".0%"),
                    template="plotly_white",
                    title="Campaign Performance — Gross Profit vs Spend with ROI",
                    yaxis=dict(tickprefix="\u09f3"),
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    df[["Campaign", "Spend", "New_Customers", "CAC", "LTV",
                        "Total_GP", "ROI", "LTV_CAC"]].style.format({
                        "Spend":         fmt,
                        "CAC":           fmt,
                        "LTV":           fmt,
                        "Total_GP":      fmt,
                        "New_Customers": "{:,.1f}",
                        "ROI":           "{:.1%}",
                        "LTV_CAC":       "{:.2f}x",
                    }),
                    hide_index=True, use_container_width=True,
                )
                best_roi  = df.loc[df["ROI"].idxmax(), "Campaign"] if not df.empty else "N/A"
                worst_roi = df.loc[df["ROI"].idxmin(), "Campaign"] if not df.empty else "N/A"
                self._insight_box(
                    what=(
                        f"Best ROI campaign: **{best_roi}** ({df['ROI'].max():.1%}). "
                        f"Lowest ROI: **{worst_roi}** ({df['ROI'].min():.1%}). "
                        f"Total spend: {fmt(df['Spend'].sum())}. "
                        f"Total GP generated: {fmt(df['Total_GP'].sum())}."
                    ),
                    recommendation=(
                        "Scale budget into campaigns with LTV:CAC ≥ 3. "
                        f"Pause **{worst_roi}** if its LTV:CAC ratio is below 1.0. "
                        "Increase content-marketing investment if it shows high ROI at low spend."
                    ),
                    context_data=df[["Campaign", "ROI", "LTV_CAC", "CAC", "Total_GP"]].to_dict(orient="records"),
                )

            with tab2:
                max_cac = df["CAC"].max() * 1.2
                line_x  = np.linspace(0, max_cac, 100)
                fig2    = px.scatter(
                    df, x="CAC", y="LTV",
                    size="New_Customers", color="Campaign",
                    text="Campaign", size_max=60,
                    title="LTV vs CAC", template="plotly_white",
                )
                fig2.add_trace(go.Scatter(
                    x=line_x, y=line_x * 3, mode="lines",
                    name="3:1 Threshold", line=dict(dash="dash", color="green"),
                ))
                fig2.add_trace(go.Scatter(
                    x=line_x, y=line_x, mode="lines",
                    name="Breakeven", line=dict(dash="dot", color="red"),
                ))
                fig2.update_traces(textposition="top center")
                st.plotly_chart(fig2, use_container_width=True)
                self._insight_box(
                    what=(
                        "Points above the green 3:1 line are highly profitable. "
                        f"LTV per customer: {fmt(df['LTV'].mean())} average."
                    ),
                    recommendation=(
                        "Aim for LTV:CAC ≥ 3 across all campaigns. "
                        "Any campaign below the 1:1 breakeven line is destroying value — pause it."
                    ),
                )

            with tab3:
                budget = st.number_input(
                    "Total Budget to Allocate (৳)",
                    value=float(df["Spend"].sum()), min_value=1000.0, step=5000.0, key="mkt_bud",
                )
                pos = df[df["ROI"] > 0].copy()
                if pos.empty:
                    st.warning("No campaigns with positive ROI to optimise.")
                    return
                pos["Weight"]        = pos["ROI"] / pos["ROI"].sum()
                pos["Rec_Spend"]     = pos["Weight"] * budget
                pos["Exp_Customers"] = pos.apply(lambda r: safe_div(r["Rec_Spend"], r["CAC"]), axis=1)
                pos["Exp_GP"]        = pos["Exp_Customers"] * pos["LTV"]
                pos = pos.fillna(0.0)

                c1, c2 = st.columns(2)
                with c1:
                    fig3 = px.pie(
                        pos, names="Campaign", values="Rec_Spend",
                        hole=0.4, title="Optimal Budget Allocation", template="plotly_white",
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                with c2:
                    st.dataframe(
                        pos[["Campaign", "Rec_Spend", "Exp_Customers", "Exp_GP"]].style.format({
                            "Rec_Spend":     fmt,
                            "Exp_Customers": "{:,.1f}",
                            "Exp_GP":        fmt,
                        }),
                        hide_index=True, use_container_width=True,
                    )
                    st.metric("Expected New Customers", f"{pos['Exp_Customers'].sum():,.0f}")
                    st.metric("Expected Gross Profit",   fmt(pos["Exp_GP"].sum()))
