"""
modules/customer_analytics.py  ·  FinOx Suite
===============================================
Customer Segmentation & CLV using K-Means Clustering.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from core.base_module import BaseModule
from utils.formatters import fmt, read_file, safe_div


class CustomerAnalyticsModule(BaseModule):
    PAGE_ICON  = "👥"
    PAGE_TITLE = "Customer Analytics"

    FEATURES = ["Annual_Spend", "Items_Purchased", "Purchase_Frequency"]

    def render(self) -> None:
        self._page_header(
            "👥 Customer Segmentation & CLV (K-Means Clustering)",
            "Upload CSV with CustomerID, Annual_Spend, Items_Purchased, Purchase_Frequency "
            "— or edit sample data",
        )
        with st.container(border=True):
            df = self._load()
            df = st.data_editor(df, num_rows="dynamic", height=250, key="ca_ed")
            if df.empty:
                return

            missing = [c for c in self.FEATURES if c not in df.columns]
            if missing:
                self._error_box(f"Missing columns: **{', '.join(missing)}**")
                return

            feats = df[self.FEATURES].dropna()
            if len(feats) < 3:
                self._error_box("Need at least 3 valid rows for clustering.")
                return

            k = st.slider(
                "Number of Segments (k)", 2, min(6, len(feats) - 1),
                min(3, len(feats) - 1), key="ca_k",
            )
            X       = StandardScaler().fit_transform(feats)
            labels  = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)
            df.loc[feats.index, "Segment"] = [f"Segment {i + 1}" for i in labels]

            tab1, tab2, tab3 = st.tabs([
                "📊 3-D Scatter", "📈 Elbow Chart", "📋 Segment Profiles",
            ])

            with tab1:
                fig = px.scatter_3d(
                    df, x="Annual_Spend", y="Purchase_Frequency",
                    z="Items_Purchased", color="Segment",
                    title="Customer Segments — 3D View",
                    template="plotly_white",
                )
                fig.update_traces(marker=dict(size=6, opacity=0.85))
                st.plotly_chart(fig, use_container_width=True)

                best_seg = (
                    df.groupby("Segment")["Annual_Spend"].mean().idxmax()
                    if "Segment" in df.columns else "N/A"
                )
                total_clv = df["Annual_Spend"].sum()
                self._insight_box(
                    what=(
                        f"{k} customer segments identified. "
                        f"Highest-value segment: **{best_seg}**. "
                        f"Total portfolio CLV: {fmt(total_clv)}/year."
                    ),
                    recommendation=(
                        f"Direct loyalty programmes at **{best_seg}** to protect revenue. "
                        "Run re-engagement campaigns for low-frequency segments. "
                        "Use the elbow chart to validate the optimal k."
                    ),
                    context_data={
                        "Segments": k,
                        "Top Segment": best_seg,
                        "Total Annual Spend": fmt(total_clv),
                        "Avg Spend per Customer": fmt(safe_div(total_clv, len(df))),
                    },
                )

            with tab2:
                inertias: list[float] = []
                k_range = range(2, min(10, len(feats)))
                for ki in k_range:
                    inertias.append(
                        float(KMeans(n_clusters=ki, random_state=42, n_init=10).fit(X).inertia_)
                    )
                fig2 = px.line(
                    x=list(k_range), y=inertias, markers=True,
                    title="Elbow Chart — choose k at the bend",
                    labels={"x": "Number of Clusters (k)", "y": "Inertia"},
                    template="plotly_white",
                )
                st.plotly_chart(fig2, use_container_width=True)

            with tab3:
                prof = (
                    df.groupby("Segment")
                    .agg(
                        Count=("Segment", "count"),
                        Avg_Spend=("Annual_Spend", "mean"),
                        Avg_Freq=("Purchase_Frequency", "mean"),
                        Avg_Items=("Items_Purchased", "mean"),
                    )
                    .reset_index()
                )
                st.dataframe(
                    prof.style.format({
                        "Avg_Spend": fmt,
                        "Avg_Freq":  "{:.1f}",
                        "Avg_Items": "{:.1f}",
                    }),
                    use_container_width=True, hide_index=True,
                )

    def _load(self) -> pd.DataFrame:
        up = st.file_uploader(
            "Upload Customer CSV or Excel", type=["csv", "xlsx", "xls"], key="ca_up"
        )
        if up is not None:
            try:
                df = read_file(up)
                if all(c in df.columns for c in self.FEATURES):
                    return df
                st.warning(f"Missing columns: {self.FEATURES}. Using sample data.")
            except Exception as exc:
                st.error(f"Could not read file: {exc}")

        return pd.DataFrame({
            "CustomerID":         [101, 102, 103, 104, 105, 106, 107, 108],
            "Annual_Spend":       [50_000, 150_000, 62_000, 250_000, 80_000, 320_000, 42_000, 195_000],
            "Items_Purchased":    [5, 20, 8, 25, 12, 30, 4, 22],
            "Purchase_Frequency": [2, 12, 4, 10, 6, 14, 3, 11],
        })
