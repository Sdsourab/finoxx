"""
modules/inventory.py  ·  FinOx Suite
======================================
Advanced Inventory Management Suite (EOQ, Safety Stock, Simulation).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div


class InventoryModule(BaseModule):
    PAGE_ICON  = "📦"
    PAGE_TITLE = "Inventory Management"

    def render(self) -> None:
        self._page_header(
            "📦 Advanced Inventory Management Suite",
            "EOQ · Safety Stock · Reorder Point · Quantity Discounts · Dynamic Simulation",
        )
        with st.container(border=True):
            st.info("Optimise inventory with EOQ, Safety Stock, Reorder Point, and dynamic simulation.")

            ann_dem = self.qty * 12

            st.markdown("#### Core Parameters")
            c1, c2, c3, c4 = st.columns(4)
            uc  = c1.number_input("Unit Cost (৳)",     0.01, 1e9,  200.0, key="inv_uc")
            oc  = c2.number_input("Order Cost (৳)",    1.0,  1e5, 5000.0, key="inv_oc")
            hcp = c3.number_input("Holding Cost %",    1.0,  100.0, 25.0, key="inv_hcp")
            hcu = uc * (hcp / 100)
            c4.metric("Holding Cost/Unit/Yr", f"\u09f3{hcu:,.2f}")

            eoq = float(np.sqrt((2 * ann_dem * oc) / hcu)) if hcu > 0 else 0.0

            st.markdown("#### Safety Stock & Reorder Point")
            c1, c2, c3 = st.columns(3)
            lt   = c1.number_input("Lead Time (Days)",       1, 365,   14, key="inv_lt")
            dstd = c2.number_input("Daily Demand Std Dev",   0.0, 1000.0, 10.0, key="inv_ds")
            sl   = c3.slider("Service Level %",              80.0, 99.9, 95.0, key="inv_sl")

            try:
                from scipy.stats import norm
                z = float(norm.ppf(sl / 100))
            except ImportError:
                z = 1.645  # ~95% fallback

            ss  = z * dstd * float(np.sqrt(lt))
            dd  = ann_dem / 365.0
            rop = dd * lt + ss

            tab1, tab2, tab3 = st.tabs([
                "📊 EOQ & ROP", "💰 Quantity Discounts", "🌊 Simulation"
            ])

            with tab1:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("EOQ",          f"{eoq:,.0f} units")
                c2.metric("ROP",          f"{rop:,.0f} units")
                c3.metric("Safety Stock", f"{ss:,.0f} units")
                tc = (ann_dem * uc + safe_div(ann_dem, eoq) * oc + (eoq / 2) * hcu) if eoq > 0 else 0.0
                c4.metric("Total Annual Cost", fmt(tc))

                qr  = np.linspace(max(1.0, eoq / 4), eoq * 4, 300)
                cdf = pd.DataFrame({
                    "Order Qty": qr,
                    "Holding":   (qr / 2) * hcu,
                    "Ordering":  (ann_dem / qr) * oc,
                })
                cdf["Total"] = cdf["Holding"] + cdf["Ordering"]
                fig = px.line(
                    cdf, x="Order Qty", y=["Holding", "Ordering", "Total"],
                    title="EOQ Cost Curves", template="plotly_white",
                )
                fig.add_vline(
                    x=eoq, line_dash="dash", line_color="green",
                    annotation_text=f"EOQ={eoq:,.0f}",
                )
                st.plotly_chart(fig, use_container_width=True)

                self._insight_box(
                    what=(
                        f"EOQ: {eoq:,.0f} units. ROP: {rop:,.0f} units. "
                        f"Safety stock: {ss:,.0f} units at {sl:.0f}% service level. "
                        f"Total annual inventory cost: {fmt(tc)}."
                    ),
                    recommendation=(
                        f"Order {eoq:,.0f} units each time. Reorder when stock hits "
                        f"{rop:,.0f} units. If stockouts occur, increase safety stock "
                        "or negotiate shorter lead times with suppliers."
                    ),
                    context_data={
                        "EOQ":              f"{eoq:,.0f}",
                        "ROP":              f"{rop:,.0f}",
                        "Safety Stock":     f"{ss:,.0f}",
                        "Service Level":    f"{sl:.0f}%",
                        "Total Annual Cost": fmt(tc),
                        "Annual Demand":    f"{ann_dem:,.0f}",
                    },
                )

            with tab2:
                st.info("Enter supplier price tiers to find the optimal order quantity.")
                disc = st.data_editor(
                    pd.DataFrame({
                        "Min Qty":  [1,   500,  1000],
                        "Max Qty":  [499, 999,  99999],
                        "Unit Cost": [200, 195,  190],
                    }),
                    num_rows="dynamic", use_container_width=True, key="inv_disc",
                )
                if not disc.empty:
                    res: list[dict] = []
                    for _, row in disc.iterrows():
                        q   = max(1.0, float(row["Min Qty"]))
                        pr  = float(row["Unit Cost"])
                        hc  = pr * (hcp / 100)
                        tc2 = ann_dem * pr + safe_div(ann_dem, q) * oc + (q / 2) * hc
                        res.append({"Tier": f"≥{q:,.0f} units", "Total Annual Cost": tc2})
                    rdf = pd.DataFrame(res)
                    opt = rdf.loc[rdf["Total Annual Cost"].idxmin()]
                    fig2 = px.bar(
                        rdf, x="Tier", y="Total Annual Cost",
                        text=rdf["Total Annual Cost"].apply(fmt),
                        title="Cost by Discount Tier", template="plotly_white",
                        color="Total Annual Cost", color_continuous_scale="RdYlGn_r",
                    )
                    fig2.update_traces(textposition="outside")
                    st.plotly_chart(fig2, use_container_width=True)
                    self._insight_box(
                        what=f"Optimal tier: **{opt['Tier']}** with total cost {fmt(opt['Total Annual Cost'])}.",
                        recommendation=(
                            f"Order at tier **{opt['Tier']}** to minimise total annual cost. "
                            "Ensure storage capacity can handle the larger batch before committing."
                        ),
                        context_data=rdf.to_dict(orient="records"),
                    )

            with tab3:
                if st.button("▶️ Run 365-Day Simulation", type="primary", key="inv_sim"):
                    inv_lvl: list[float] = [float(eoq + ss)]
                    on_ord = 0.0
                    arr    = -1
                    rng    = np.random.default_rng(99)
                    for day in range(1, 365):
                        dem = max(0.0, float(rng.normal(dd, dstd)))
                        lv  = max(0.0, inv_lvl[-1] - dem)
                        if day == arr:
                            lv    += on_ord
                            on_ord = 0.0
                            arr    = -1
                        if lv <= rop and on_ord == 0.0:
                            on_ord = eoq
                            arr    = day + int(lt)
                        inv_lvl.append(lv)
                    sdf = pd.DataFrame({
                        "Day":             range(365),
                        "Inventory Level": inv_lvl[:365],
                    })
                    fig3 = px.area(
                        sdf, x="Day", y="Inventory Level",
                        title="365-Day Inventory Simulation",
                        color_discrete_sequence=["#17becf"],
                        template="plotly_white",
                    )
                    fig3.add_hline(y=rop, line_dash="dash", line_color="orange",
                                   annotation_text=f"ROP={rop:,.0f}")
                    fig3.add_hline(y=ss,  line_dash="dot",  line_color="red",
                                   annotation_text=f"SS={ss:,.0f}")
                    st.plotly_chart(fig3, use_container_width=True)
                    self._insight_box(
                        what=(
                            "Sawtooth inventory pattern shows daily depletion and "
                            f"replenishment cycles. Min level simulated: "
                            f"{min(inv_lvl[:365]):,.0f} units."
                        ),
                        recommendation=(
                            "If inventory frequently dips below ROP before orders arrive, "
                            "increase safety stock or negotiate shorter lead times."
                        ),
                    )
                else:
                    st.info("Click ▶️ Run 365-Day Simulation to generate the chart.")
