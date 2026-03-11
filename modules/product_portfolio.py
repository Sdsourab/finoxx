"""
modules/product_portfolio.py  ·  FinOx Suite
==============================================
Product Portfolio & BCG Matrix Analysis.

FIX (v2.1) — AttributeError: 'list' object has no attribute 'items'
----------------------------------------------------------------------
BEFORE:
    context_data=df[["Product", "BCG", "Revenue",
                      "Market_Growth_Rate", "Relative_Market_Share"]
                    ].to_dict(orient="records")

    df.to_dict(orient="records") returns a LIST of dicts.
    _build_enriched_context() calls context_data.items() — lists have no .items().
    Result: AttributeError crash every time BCG Matrix loaded.

FIX:
    Pass a proper flat dict summarising the portfolio instead of the raw records
    list. This also produces richer, more focused AI context:
    - Summary KPIs (totals, counts per quadrant) are at the top level.
    - Per-product detail lines are flattened as individual string entries.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt


class ProductPortfolioModule(BaseModule):
    PAGE_ICON  = "⭐"
    PAGE_TITLE = "BCG Matrix"

    _SAMPLE = pd.DataFrame({
        "Product":                ["Product A", "Product B", "Product C", "Product D", "Product E"],
        "Revenue":                [500_000, 300_000, 150_000, 800_000, 100_000],
        "Market_Growth_Rate":     [12.0, 8.0, 5.0, 18.0, 3.0],
        "Relative_Market_Share":  [1.5, 0.8, 0.4, 0.6, 1.2],
    })

    def render(self) -> None:
        self._page_header(
            "⭐ Product Portfolio & BCG Matrix",
            "Edit your product data — Relative Market Share > 1.0 means you lead that segment",
        )
        with st.container(border=True):
            df = st.data_editor(
                self._SAMPLE, num_rows="dynamic", height=220, key="pp_ed"
            )
            if df.empty:
                self._info_box("Add at least one product to begin.")
                return

            def _bcg(row: pd.Series) -> str:
                g = float(row.get("Market_Growth_Rate",     0))
                s = float(row.get("Relative_Market_Share",  0))
                if g >= 10 and s >= 1.0:
                    return "⭐ Star"
                if g < 10  and s >= 1.0:
                    return "🐄 Cash Cow"
                if g >= 10 and s < 1.0:
                    return "❓ Question Mark"
                return "🐕 Dog"

            df["BCG"] = df.apply(_bcg, axis=1)

            tab1, tab2 = st.tabs(["📍 BCG Matrix", "🌳 Revenue Treemap"])

            with tab1:
                fig = px.scatter(
                    df, x="Relative_Market_Share", y="Market_Growth_Rate",
                    size="Revenue", color="BCG", text="Product", size_max=80,
                    color_discrete_map={
                        "⭐ Star":          "#f7b731",
                        "🐄 Cash Cow":      "#20bf6b",
                        "❓ Question Mark": "#4fc3f7",
                        "🐕 Dog":           "#ef5350",
                    },
                    title="BCG Growth-Share Matrix",
                    template="plotly_white",
                )
                fig.add_hline(
                    y=10, line_dash="dash", line_color="grey",
                    annotation_text="Growth threshold (10%)",
                )
                fig.add_vline(
                    x=1.0, line_dash="dash", line_color="grey",
                    annotation_text="Market leader (1.0x)",
                )
                fig.update_traces(textposition="top center")
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(
                    df[["Product", "BCG", "Revenue", "Market_Growth_Rate",
                        "Relative_Market_Share"]].style.format({
                        "Revenue":               fmt,
                        "Market_Growth_Rate":    "{:.1f}%",
                        "Relative_Market_Share": "{:.2f}x",
                    }),
                    hide_index=True, use_container_width=True,
                )

                stars     = df[df["BCG"] == "⭐ Star"]["Product"].tolist()
                cash_cows = df[df["BCG"] == "🐄 Cash Cow"]["Product"].tolist()
                q_marks   = df[df["BCG"] == "❓ Question Mark"]["Product"].tolist()
                dogs      = df[df["BCG"] == "🐕 Dog"]["Product"].tolist()
                total_rev = df["Revenue"].sum()

                # ── FIX: build flat dict instead of df.to_dict(orient="records") ──
                # to_dict(orient="records") returns a LIST, which has no .items()
                # and crashes _build_enriched_context.  Flatten here instead.
                context_dict: dict = {
                    "Total Portfolio Revenue":   fmt(total_rev),
                    "Total Products":            len(df),
                    "Stars":                     ", ".join(stars) or "None",
                    "Cash Cows":                 ", ".join(cash_cows) or "None",
                    "Question Marks":            ", ".join(q_marks) or "None",
                    "Dogs":                      ", ".join(dogs) or "None",
                    "Star Revenue":              fmt(df[df["BCG"] == "⭐ Star"]["Revenue"].sum()),
                    "Cash Cow Revenue":          fmt(df[df["BCG"] == "🐄 Cash Cow"]["Revenue"].sum()),
                }
                # Add per-product lines as individual entries (still a flat dict)
                for _, row in df.iterrows():
                    key = f"Product — {row['Product']}"
                    context_dict[key] = (
                        f"{row['BCG']} | Rev: {fmt(row['Revenue'])} | "
                        f"Growth: {row['Market_Growth_Rate']:.1f}% | "
                        f"RMS: {row['Relative_Market_Share']:.2f}x"
                    )

                self._insight_box(
                    what=(
                        f"Stars: {stars or 'None'}. Cash Cows: {cash_cows or 'None'}. "
                        f"Dogs: {dogs or 'None'}. "
                        f"Total portfolio revenue: {fmt(total_rev)}."
                    ),
                    recommendation=(
                        "Invest in Stars to maintain growth momentum. "
                        "Harvest Cash Cows to fund Question Marks. "
                        f"{'Consider divesting Dogs to free up capital.' if dogs else ''}"
                    ),
                    context_data=context_dict,
                )

            with tab2:
                fig2 = px.treemap(
                    df, path=["BCG", "Product"], values="Revenue",
                    color="Market_Growth_Rate",
                    color_continuous_scale="RdYlGn",
                    title="Revenue Treemap by BCG Category",
                    template="plotly_white",
                )
                st.plotly_chart(fig2, use_container_width=True)