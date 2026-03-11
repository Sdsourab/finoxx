"""
modules/monte_carlo.py  ·  FinOx Suite
========================================
Monte Carlo Risk Simulation Lab.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div


class MonteCarloModule(BaseModule):
    PAGE_ICON  = "🎲"
    PAGE_TITLE = "Monte Carlo"

    def render(self) -> None:
        self._page_header(
            "🎲 Monte Carlo Risk Simulation Lab",
            "Simulate monthly profit under uncertainty across thousands of scenarios",
        )
        with st.container(border=True):
            n = st.select_slider(
                "Simulation Runs",
                [1_000, 5_000, 10_000, 20_000, 50_000], 10_000, key="mc_n",
            )
            c1, c2 = st.columns(2)
            qty_std = c1.slider(
                "Qty Volatility (Std Dev)", 0,
                max(1, int(self.qty * 0.5)),
                int(self.qty * 0.2), key="mc_q",
            )
            vc_std = c2.slider(
                "Variable Cost Volatility (Std Dev)",
                0.0, max(0.1, self.var_cost * 0.5),
                self.var_cost * 0.15, key="mc_vc",
            )

            if st.button("▶️ Run Simulation", type="primary", key="mc_run"):
                rng     = np.random.default_rng()
                s_qty   = np.maximum(0, rng.normal(self.qty,      qty_std, n))
                s_vc    = np.maximum(0, rng.normal(self.var_cost, vc_std,  n))
                results = (self.price - s_vc) * s_qty - self.fixed_monthly

                prob  = float(np.mean(results > 0))
                avg   = float(np.mean(results))
                var5  = float(np.percentile(results, 5))
                cvar5 = float(np.mean(results[results <= var5]))

                fig = px.histogram(
                    x=results, nbins=120,
                    title=f"Monthly Profit Distribution ({n:,} simulations)",
                    labels={"x": "Monthly Profit (৳)"},
                    color_discrete_sequence=["#1f77b4"],
                    template="plotly_white",
                )
                fig.add_vline(
                    x=0, line_dash="dash", line_color="red",
                    annotation_text="Breakeven",
                )
                fig.add_vline(
                    x=var5, line_dash="dot", line_color="orange",
                    annotation_text=f"VaR 5% = {fmt(var5)}",
                )
                fig.update_layout(yaxis_title="Frequency", xaxis=dict(tickprefix="\u09f3"))
                st.plotly_chart(fig, use_container_width=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Prob. of Profit",       f"{prob:.1%}")
                c2.metric("Expected Profit",       fmt(avg))
                c3.metric("VaR (5th percentile)", fmt(var5))
                c4.metric("CVaR (Exp. Shortfall)", fmt(cvar5))

                if prob >= 0.90:
                    st.success(f"🟢 Low Risk — {prob:.0%} probability of monthly profitability.")
                elif prob >= 0.65:
                    st.warning(f"🟡 Moderate Risk — {prob:.0%} probability of monthly profitability.")
                else:
                    st.error(f"🔴 High Risk — Only {prob:.0%} probability of monthly profitability.")

                with st.expander("📊 Full Percentile Table"):
                    pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
                    st.dataframe(
                        pd.DataFrame({
                            "Percentile": [f"P{p}" for p in pcts],
                            "Monthly Profit": [fmt(float(np.percentile(results, p))) for p in pcts],
                        }),
                        hide_index=True, use_container_width=True,
                    )

                self._insight_box(
                    what=(
                        f"Across {n:,} simulations: expected monthly profit {fmt(avg)}, "
                        f"VaR (5th pct) {fmt(var5)}, CVaR {fmt(cvar5)}, "
                        f"probability of profit {prob:.1%}."
                    ),
                    recommendation=(
                        f"VaR at the 5th percentile is {fmt(var5)} — this is your downside risk floor. "
                        f"{'Raise price or cut variable costs to improve the profit probability above 80%.' if prob < 0.80 else 'Profit probability is healthy. Monitor the CVaR figure when scaling volumes.'}"
                    ),
                    context_data={
                        "Simulations":         n,
                        "Expected Profit":     fmt(avg),
                        "VaR 5%":              fmt(var5),
                        "CVaR":                fmt(cvar5),
                        "Profit Probability":  f"{prob:.1%}",
                        "Unit Price":          fmt(self.price),
                        "Variable Cost":       fmt(self.var_cost),
                        "Fixed Monthly Cost":  fmt(self.fixed_monthly),
                    },
                )
            else:
                st.info("Click ▶️ Run Simulation to generate results.")
