"""
modules/forecasting.py  ·  FinOx Suite
========================================
Advanced Time-Series Forecasting (ARIMA).
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, read_file


class ForecastingModule(BaseModule):
    PAGE_ICON  = "🔮"
    PAGE_TITLE = "Forecasting"

    def render(self) -> None:
        self._page_header(
            "🔮 Advanced Time-Series Forecasting (ARIMA)",
            "Upload CSV with 'Date' and 'Revenue' columns (monthly), or edit sample data",
        )
        with st.container(border=True):
            df = self._load()
            df = st.data_editor(
                df, num_rows="dynamic", height=250,
                column_config={
                    "Date": st.column_config.DateColumn(format="YYYY-MM-DD")
                },
                key="fc_ed",
            )

            with st.expander("🔧 ARIMA Order (p,d,q)"):
                c1, c2, c3 = st.columns(3)
                p = c1.slider("p (AR order)",    0, 7, 5, key="fc_p")
                d = c2.slider("d (Differencing)", 0, 2, 1, key="fc_d")
                q = c3.slider("q (MA order)",     0, 7, 0, key="fc_q")

            steps = st.slider("Forecast Horizon (months)", 3, 36, 12, key="fc_h")

            if df.empty:
                self._info_box("Add data to begin forecasting.")
                return

            try:
                ts = df.copy()
                ts["Date"] = pd.to_datetime(ts["Date"])
                ts = ts.set_index("Date")["Revenue"].asfreq("MS").ffill()
            except Exception as exc:
                st.error(f"Data preparation error: {exc}")
                return

            try:
                from statsmodels.tsa.arima.model import ARIMA
            except ImportError:
                st.error("statsmodels is required. Run: pip install statsmodels")
                return

            with st.spinner("Training ARIMA model…"):
                try:
                    model   = ARIMA(ts, order=(p, d, q)).fit()
                    fc      = model.get_forecast(steps=steps)
                    fc_mean = fc.predicted_mean
                    ci      = fc.conf_int()
                except Exception as exc:
                    st.error(f"ARIMA failed: {exc}. Try adjusting (p,d,q) parameters.")
                    return

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ts.index, y=ts, mode="lines+markers",
                name="Historical", line=dict(color="#1f77b4"),
            ))
            fig.add_trace(go.Scatter(
                x=fc_mean.index, y=fc_mean, mode="lines",
                name="Forecast", line=dict(dash="dash", color="#d62728", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=ci.index, y=ci.iloc[:, 1], mode="lines",
                line_color="rgba(0,0,0,0)", showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=ci.index, y=ci.iloc[:, 0],
                fill="tonexty", mode="lines",
                name="95% CI", fillcolor="rgba(255,99,71,0.15)",
                line_color="rgba(0,0,0,0)",
            ))
            fig.update_layout(
                title="Revenue Forecast with 95% Confidence Interval",
                template="plotly_white",
                yaxis=dict(tickprefix="\u09f3"),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Forecast table
            tbl = pd.DataFrame({
                "Forecast":   fc_mean,
                "Lower CI":   ci.iloc[:, 0],
                "Upper CI":   ci.iloc[:, 1],
            })
            tbl.index = tbl.index.strftime("%b %Y")
            st.dataframe(tbl.style.format(fmt), use_container_width=True)

            with st.expander("📊 Model Diagnostics"):
                c1, c2 = st.columns(2)
                c1.metric("AIC", f"{model.aic:.1f}")
                c2.metric("BIC", f"{model.bic:.1f}")

            trend = "upward 📈" if fc_mean.iloc[-1] > fc_mean.iloc[0] else "downward 📉"
            self._insight_box(
                what=(
                    f"ARIMA({p},{d},{q}) forecast over {steps} months. "
                    f"Trend: {trend}. "
                    f"Final forecast value: {fmt(fc_mean.iloc[-1])}."
                ),
                recommendation=(
                    "Use the forecast trend to guide inventory, hiring, and budget planning. "
                    "Wide confidence bands indicate higher uncertainty — "
                    "increase historical data length for better accuracy."
                ),
                context_data={
                    "ARIMA Order":      f"({p},{d},{q})",
                    "Forecast Horizon": f"{steps} months",
                    "First Forecast":   fmt(fc_mean.iloc[0]),
                    "Last Forecast":    fmt(fc_mean.iloc[-1]),
                    "Trend":            trend,
                    "AIC":              f"{model.aic:.1f}",
                    "BIC":              f"{model.bic:.1f}",
                },
            )

    def _load(self) -> pd.DataFrame:
        up = st.file_uploader(
            "Upload Revenue CSV or Excel", type=["csv", "xlsx", "xls"], key="fc_up"
        )
        if up is not None:
            try:
                df = read_file(up)
                df["Date"] = pd.to_datetime(df["Date"])
                if "Date" in df.columns and "Revenue" in df.columns:
                    return df
                st.warning("File must contain 'Date' and 'Revenue' columns. Using sample.")
            except Exception as exc:
                st.error(f"Could not read file: {exc}")

        vals = [
            180, 195, 210, 205, 220, 235, 250, 240,
            260, 275, 300, 280, 200, 215, 230, 225,
            240, 255, 270, 260, 280, 295, 320, 300,
        ]
        return pd.DataFrame({
            "Date":    pd.date_range("2022-01-01", periods=24, freq="MS"),
            "Revenue": [v * 1000 for v in vals],
        })
