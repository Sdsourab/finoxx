"""
modules/geo_analytics.py  ·  FinOx Suite
==========================================
Advanced Geospatial Intelligence Suite.

FIX (v2.1) — AttributeError: 'list' object has no attribute 'items'
----------------------------------------------------------------------
BEFORE:
    context_data=agg.sort_values("Total_Sales", ascending=False)
                   .head(5).to_dict(orient="records")

    Returns a LIST of dicts → _build_enriched_context crashes on .items().

FIX:
    Build a proper flat dict with summary KPIs + per-city detail rows.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, read_file


class GeoAnalyticsModule(BaseModule):
    PAGE_ICON  = "🗺️"
    PAGE_TITLE = "Geo Analytics"

    COLS = ["Region", "City", "Latitude", "Longitude",
            "Product_Category", "Sales", "Transactions"]

    def render(self) -> None:
        self._page_header(
            "🗺️ Advanced Geospatial Intelligence Suite",
            "Upload sales data with location coordinates to map regional performance",
        )
        with st.container(border=True):
            st.info(
                "Upload CSV with: **Region, City, Latitude, Longitude, "
                "Product_Category, Sales, Transactions**"
            )
            df = self._load()
            if df is None:
                return

            tab1, tab2, tab3 = st.tabs([
                "📍 Map View", "📈 Regional Performance", "📦 Product Deep-Dive"
            ])

            with tab1:
                agg = (
                    df.groupby(["City", "Region", "Latitude", "Longitude"])
                    .agg(Total_Sales=("Sales", "sum"), Transactions=("Transactions", "sum"))
                    .reset_index()
                )
                fig = px.scatter_geo(
                    agg, lat="Latitude", lon="Longitude",
                    size="Total_Sales", color="Total_Sales",
                    hover_name="City",
                    hover_data={
                        "Region": True, "Total_Sales": ":,.0f",
                        "Transactions": True,
                        "Latitude": False, "Longitude": False,
                    },
                    projection="natural earth",
                    color_continuous_scale=px.colors.sequential.Plasma,
                    title="Sales by City",
                )
                fig.update_geos(
                    scope="asia",
                    center=dict(lon=90.35, lat=23.68),
                    lataxis_range=[20, 27],
                    lonaxis_range=[88, 93],
                )
                fig.update_layout(margin=dict(r=0, t=40, l=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

                top = agg.loc[agg["Total_Sales"].idxmax()]
                top5 = agg.sort_values("Total_Sales", ascending=False).head(5)

                # ── FIX: flat dict instead of top5.to_dict(orient="records") ────
                context_dict: dict = {
                    "Top City":              str(top["City"]),
                    "Top City Sales":        fmt(top["Total_Sales"]),
                    "Top City Transactions": int(top["Transactions"]),
                    "Top City Region":       str(top["Region"]),
                    "Total Cities":          len(agg),
                    "Grand Total Sales":     fmt(agg["Total_Sales"].sum()),
                    "Total Transactions":    int(agg["Transactions"].sum()),
                }
                # Add per-city rows as flat entries (top 5)
                for rank, (_, row) in enumerate(top5.iterrows(), start=1):
                    key = f"#{rank} — {row['City']}"
                    context_dict[key] = (
                        f"Sales: {fmt(row['Total_Sales'])} | "
                        f"Txns: {int(row['Transactions'])} | "
                        f"Region: {row['Region']}"
                    )

                self._insight_box(
                    what=(
                        f"Top city: **{top['City']}** with {fmt(top['Total_Sales'])} in sales "
                        f"across {int(top['Transactions'])} transactions."
                    ),
                    recommendation=(
                        f"Prioritise inventory and marketing budget in **{top['City']}**. "
                        "Investigate low-performing cities for potential market expansion."
                    ),
                    context_data=context_dict,
                )

            with tab2:
                ragg = (
                    df.groupby("Region")
                    .agg(Total_Sales=("Sales", "sum"), Txns=("Transactions", "sum"))
                    .reset_index()
                )
                ragg["Avg_Value"] = ragg["Total_Sales"] / ragg["Txns"].replace(0, 1)
                ragg = ragg.sort_values("Total_Sales", ascending=False)

                c1, c2 = st.columns([1, 2])
                with c1:
                    st.dataframe(
                        ragg.style.format({"Total_Sales": fmt, "Avg_Value": fmt}),
                        hide_index=True, use_container_width=True,
                    )
                with c2:
                    fig2 = px.bar(
                        ragg, x="Region", y="Total_Sales",
                        color="Avg_Value", color_continuous_scale=px.colors.sequential.Viridis,
                        title="Sales by Region (colour = Avg Transaction Value)",
                        template="plotly_white",
                    )
                    fig2.update_layout(yaxis=dict(tickprefix="\u09f3"))
                    st.plotly_chart(fig2, use_container_width=True)

            with tab3:
                fig3 = px.sunburst(
                    df, path=["Region", "Product_Category"], values="Sales",
                    color="Sales",
                    color_continuous_scale=px.colors.sequential.Blues,
                    title="Region → Product Category Revenue Breakdown",
                )
                fig3.update_layout(margin=dict(r=10, t=50, l=10, b=10))
                st.plotly_chart(fig3, use_container_width=True)

    def _load(self) -> pd.DataFrame | None:
        up = st.file_uploader(
            "Upload Sales CSV or Excel", type=["csv", "xlsx", "xls"], key="geo_up"
        )
        if up is not None:
            try:
                df   = read_file(up)
                miss = [c for c in self.COLS if c not in df.columns]
                if miss:
                    self._error_box(f"Missing columns: {miss}")
                    return None
                return df
            except Exception as exc:
                st.error(f"Could not read file: {exc}")
                return None

        return pd.DataFrame({
            "Region":           ["Central", "South-East", "North", "South-West",
                                  "Central", "South-East", "North", "Central"],
            "City":             ["Dhaka", "Chittagong", "Sylhet", "Khulna",
                                  "Gazipur", "Cox's Bazar", "Rangpur", "Narayanganj"],
            "Latitude":         [23.8103, 22.3569, 24.8949, 22.8456,
                                  23.9999, 21.4272, 25.7439, 23.6238],
            "Longitude":        [90.4125, 91.7832, 91.8687, 89.5694,
                                  90.4203, 91.9703, 89.2517, 90.5000],
            "Product_Category": ["Electronics", "Apparel", "Groceries", "Electronics",
                                  "Apparel", "Groceries", "Electronics", "Groceries"],
            "Sales":            [1_200_000, 850_000, 450_000, 600_000,
                                  750_000, 300_000, 350_000, 550_000],
            "Transactions":     [150, 120, 90, 85, 110, 80, 70, 130],
        })