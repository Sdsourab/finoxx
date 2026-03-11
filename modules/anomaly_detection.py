"""
modules/anomaly_detection.py  ·  FinOx Suite
==============================================
Anomaly Detection in Time-Series Data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, read_file


class AnomalyDetectionModule(BaseModule):
    PAGE_ICON  = "❗"
    PAGE_TITLE = "Anomaly Detection"

    def render(self) -> None:
        self._page_header(
            "❗ Anomaly Detection in Time-Series Data",
            "Z-score based rolling anomaly detection — upload your own data or use the sample",
        )
        with st.container(border=True):
            st.info("Upload CSV / Excel with **Date** and **Value** columns, or use sample data.")
            uploaded = st.file_uploader(
                "Upload CSV or Excel", type=["csv", "xlsx", "xls"], key="anom_up"
            )
            df = self._load(uploaded)
            df = st.data_editor(df, num_rows="dynamic", height=220, key="anom_ed")

            threshold = st.slider(
                "Sensitivity Threshold (Std Dev)", 1.0, 4.0, 2.5, 0.1, key="anom_thr"
            )

            df = df.copy()
            df["Date"]  = pd.to_datetime(df["Date"])
            df          = df.sort_values("Date").reset_index(drop=True)
            w           = max(3, len(df) // 10)
            df["MA"]    = df["Value"].rolling(w, center=True, min_periods=1).mean()
            df["Std"]   = df["Value"].rolling(w, center=True, min_periods=1).std().fillna(1.0)
            df["Anomaly"] = np.abs(df["Value"] - df["MA"]) > (threshold * df["Std"])

            fig = px.scatter(
                df, x="Date", y="Value", color="Anomaly",
                color_discrete_map={True: "#d62728", False: "#1f77b4"},
                title="Anomaly Detection — red dots exceed threshold",
                template="plotly_white",
            )
            fig.add_trace(go.Scatter(
                x=df["Date"], y=df["MA"], mode="lines", name="Rolling Mean",
                line=dict(color="grey", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=df["Date"], y=df["MA"] + threshold * df["Std"],
                mode="lines", name="Upper Band",
                line=dict(color="rgba(214,39,40,0.35)", width=1, dash="dash"),
                showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=df["Date"], y=df["MA"] - threshold * df["Std"],
                mode="lines", name="Lower Band",
                fill="tonexty", fillcolor="rgba(214,39,40,0.05)",
                line=dict(color="rgba(214,39,40,0.35)", width=1, dash="dash"),
                showlegend=False,
            ))
            st.plotly_chart(fig, use_container_width=True)

            anomalies = df[df["Anomaly"]][["Date", "Value"]]
            st.markdown(f"**{len(anomalies)} anomalies detected** at threshold ±{threshold}σ")
            if not anomalies.empty:
                st.dataframe(
                    anomalies.style.format({"Value": "{:.2f}"}),
                    use_container_width=True, hide_index=True,
                )

            self._insight_box(
                what=(
                    f"{len(anomalies)} anomalies detected out of {len(df)} data points "
                    f"using a ±{threshold}σ rolling window threshold."
                ),
                recommendation=(
                    "Investigate each anomaly individually — spikes may indicate "
                    "promotions, data entry errors, or external market shocks. "
                    "Tighten the threshold to catch subtler deviations."
                ),
                context_data={
                    "Total Points":     len(df),
                    "Anomalies Found":  len(anomalies),
                    "Threshold (sigma)": threshold,
                    "Anomaly Values":   anomalies["Value"].tolist() if not anomalies.empty else [],
                },
            )

    def _load(self, uploaded) -> pd.DataFrame:
        if uploaded is not None:
            try:
                df = read_file(uploaded)
                df["Date"] = pd.to_datetime(df["Date"])
                if "Date" in df.columns and "Value" in df.columns:
                    return df
                st.warning("File must contain 'Date' and 'Value' columns. Using sample data.")
            except Exception as exc:
                st.error(f"Could not read file: {exc}")
        rng   = np.random.default_rng(42)
        dates = pd.date_range("2024-01-01", periods=60)
        v     = rng.normal(200, 20, 60)
        v[5]  = 380.0
        v[20] = 40.0
        v[45] = 420.0
        return pd.DataFrame({"Date": dates, "Value": v})
