"""
modules/scenario_planner.py  ·  FinOx Suite
=============================================
Strategic Scenario Planner — NPV / IRR Analysis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div, calculate_npv, calculate_irr


class ScenarioPlannerModule(BaseModule):
    PAGE_ICON  = "🎭"
    PAGE_TITLE = "Scenario Planner"

    def render(self) -> None:
        self._page_header(
            "🎭 Strategic Scenario Planner (NPV / IRR Analysis)",
            "Model Bear, Base, and Bull scenarios to evaluate investment viability",
        )
        with st.container(border=True):
            base_rev = self.price * self.qty * 12
            c1, c2   = st.columns(2)
            capex    = c1.number_input(
                "Initial CapEx Investment (৳)",
                value=float(self.capex_init), min_value=1.0, step=100_000.0, key="sp_cap",
            )
            dr = c2.slider(
                "Discount Rate / WACC (%)", 5.0, 25.0,
                float(self.discount_rate) * 100, 0.5, key="sp_dr",
            ) / 100

            st.markdown("#### 🎛️ Scenario Parameters")
            cols = st.columns(3)
            scens: dict[str, tuple[float, float]] = {}
            defaults = {
                "Bear": (-0.10,                        0.05),
                "Base": (self.rev_growth,              self.vc_inflation),
                "Bull": (self.rev_growth * 2,          self.vc_inflation * 0.5),
            }
            emojis = {"Bear": "🐻", "Base": "📊", "Bull": "🐂"}
            colors = {"Bear": "#d62728", "Base": "#1f77b4", "Bull": "#2ca02c"}

            for i, (name, (dg, dc)) in enumerate(defaults.items()):
                with cols[i]:
                    st.markdown(f"**{emojis[name]} {name}**")
                    rg  = st.slider(
                        "Rev Growth %",   -30.0, 50.0, round(dg * 100, 1), 0.5, key=f"sp_{name}_g"
                    ) / 100
                    ci_s = st.slider(
                        "VC Inflation %", -10.0, 30.0, round(dc * 100, 1), 0.5, key=f"sp_{name}_c"
                    ) / 100
                    scens[name] = (rg, ci_s)

            fy  = self.forecast_years
            dep = safe_div(capex, self.dep_years)
            fc  = self.fixed_monthly * 12
            tr  = self.tax_rate

            results: dict[str, dict] = {}
            for name, (rg, vci) in scens.items():
                cfs: list[float] = [-capex]
                for i in range(fy):
                    rev  = base_rev * (1 + rg) ** i
                    vc   = self.var_cost * self.qty * 12 * (1 + vci) ** i
                    ebit = rev - vc - fc - dep
                    tax  = max(0.0, ebit) * tr
                    cf   = ebit - tax + dep
                    cfs.append(cf)
                pv    = calculate_npv(cfs[1:], dr)
                irr_v = calculate_irr(cfs)
                results[name] = {
                    "cash_flows": cfs, "npv": pv, "irr": irr_v, "rg": rg, "vci": vci
                }

            st.markdown("#### 📊 Scenario Comparison")
            c1, c2, c3 = st.columns(3)
            for col, (name, r) in zip([c1, c2, c3], results.items()):
                irr_disp = f"{r['irr']:.1%}" if not np.isnan(r["irr"]) else "N/A"
                col.metric(f"{emojis[name]} {name} NPV", fmt(r["npv"]))
                col.metric("IRR", irr_disp)

            # Cash flow bar chart
            fig = go.Figure()
            for name, r in results.items():
                yrs = [f"Yr {i}" for i in range(fy + 1)]
                fig.add_trace(go.Bar(
                    name=f"{emojis[name]} {name}",
                    x=yrs, y=r["cash_flows"],
                    marker_color=colors[name],
                ))
            fig.update_layout(
                barmode="group", title="Cash Flows by Scenario",
                yaxis_title="৳", yaxis=dict(tickprefix="\u09f3"),
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Cumulative cash flow line chart
            fig2 = go.Figure()
            for name, r in results.items():
                cum = np.cumsum(r["cash_flows"])
                fig2.add_trace(go.Scatter(
                    x=list(range(fy + 1)), y=cum,
                    mode="lines+markers",
                    name=f"{emojis[name]} {name}",
                    line=dict(color=colors[name], width=2),
                ))
            fig2.add_hline(y=0, line_dash="dash", line_color="black")
            fig2.update_layout(
                title="Cumulative Cash Flow",
                xaxis_title="Year",
                yaxis_title="৳", yaxis=dict(tickprefix="\u09f3"),
                template="plotly_white",
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Summary table
            rows: list[dict] = []
            for name, r in results.items():
                pb = next(
                    (i for i, v in enumerate(np.cumsum(r["cash_flows"])) if v >= 0), None
                )
                rows.append({
                    "Scenario":     f"{emojis[name]} {name}",
                    "Rev Growth":   f"{r['rg']:.1%}",
                    "VC Inflation": f"{r['vci']:.1%}",
                    "NPV":          fmt(r["npv"]),
                    "IRR":          f"{r['irr']:.1%}" if not np.isnan(r["irr"]) else "N/A",
                    "Payback":      f"Year {pb}" if pb is not None else "Not recovered",
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

            viable = [n for n, r in results.items() if r["npv"] > 0]
            self._insight_box(
                what=(
                    f"Base NPV: {fmt(results['Base']['npv'])}, "
                    f"Bear NPV: {fmt(results['Bear']['npv'])}, "
                    f"Bull NPV: {fmt(results['Bull']['npv'])}. "
                    f"WACC: {dr:.1%}."
                ),
                recommendation=(
                    "All three scenarios are viable — proceed with confidence."
                    if len(viable) == 3
                    else (
                        f"Only {', '.join(viable)} scenario(s) show positive NPV. "
                        "Stress-test assumptions before committing CapEx. "
                        "Use the Bear scenario as your downside risk estimate for board presentations."
                    )
                ),
                context_data={
                    "CapEx":        fmt(capex),
                    "WACC":         f"{dr:.1%}",
                    "Bear NPV":     fmt(results["Bear"]["npv"]),
                    "Base NPV":     fmt(results["Base"]["npv"]),
                    "Bull NPV":     fmt(results["Bull"]["npv"]),
                    "Viable Scenarios": viable,
                },
            )
