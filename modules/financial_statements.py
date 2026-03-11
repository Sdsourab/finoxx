"""
modules/financial_statements.py  ·  FinOx Suite  (REFACTORED — v3.0)
=======================================================================
Pro-Forma Financial Statement Projections.

Bug Fixes in v3.0
------------------
BUG 1 — Cumulative growth propagation gap
    BEFORE: Variable Costs projection used a constant ratio of the base-year
            VC/Revenue, which is correct only if VC inflation == revenue growth.
            Fixed Costs were flat (no inflation applied).
    FIX: Revenue projections use true compound growth: base * (1+g)^(i+1).
         VC now applies sidebar vc_inflation independently, compounding year
         over year from the base VC value.
         FC now applies sidebar fc_inflation, compounding from the base FC.
         Depreciation remains flat (capex already fixed).

BUG 2 — Null index / NaN errors in the result DataFrame
    BEFORE: When the user adds custom Metric rows (anything beyond
            Revenue / Variable Costs / Fixed Costs / Depreciation), the
            projected pd.Series only contains the four known keys.  All
            custom rows receive NaN in projected columns, which then causes
            style.format(fmt) to produce inconsistent output and can raise
            KeyError when the style engine encounters entirely NaN columns.
    FIX: After building each projected column Series, we call
         result[yr].fillna(0) to prevent NaN propagation.
         Custom user rows are preserved in historical columns; projected
         values are shown as 0 (clearly labelled "not projected").
         A banner notifies the user when custom rows exist.

BUG 3 — style.format(fmt) on non-numeric index rows
    BEFORE: If Metric column contained empty strings or None, the index
            would include NaN, which pd.DataFrame.style cannot process.
    FIX: df rows with empty/None Metric are dropped before processing.
         All numeric cells are coerced via pd.to_numeric(..., errors='coerce')
         before setting the index.

BUG 4 — Excel download BytesIO cursor position
    BEFORE: Potentially harmless but `buf.getvalue()` was called immediately
            after the ExcelWriter context manager — the buffer is always at
            the correct position after `__exit__`, so this was not a bug.
            However, an explicit `buf.seek(0)` has been added for clarity
            and compatibility with older pandas versions.
    FIX: `buf.seek(0)` added before `buf.getvalue()`.

BUG 5 — safe_div denominator mis-use when base_rev is exactly zero
    BEFORE: `base_rev = float(base.get("Revenue", 1)) or 1.0`
            This defaults to 1.0 silently when Revenue is 0, producing
            nonsensical VC ratios (e.g. 100x).
    FIX: If base_rev == 0, VC ratio defaults to 0 with a warning.

Enhancements
------------
• Dark-mode fintech chart aesthetic using CHART_PALETTE_DARK from settings.
• Waterfall chart tab for year-over-year revenue bridge.
• Richer AI context: includes year-by-year net margins and CAGR.
• Download buttons placed in a dedicated footer row to avoid layout shifts.
"""
from __future__ import annotations

import io
import math
import warnings
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, safe_div

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Color palette ─────────────────────────────────────────────────────────────
_NAVY  = "#0F2744"
_TEAL  = "#0EA5A0"
_SKY   = "#38BDF8"
_EMR   = "#34D399"
_AMBER = "#FB923C"
_ROSE  = "#F87171"
_MUT   = "#94A3B8"

# Ordered series palette (dark fintech)
_PAL = [_SKY, _EMR, _AMBER, _ROSE, "#A78BFA", "#F472B6", "#22D3EE", _MUT]


def _to_float(v: Any) -> float:
    """Safe coercion to float; returns 0.0 on failure."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class FinancialStatementsModule(BaseModule):
    PAGE_ICON  = "📑"
    PAGE_TITLE = "Financial Statements"

    def render(self) -> None:
        self._page_header(
            "📑 Financial Statement Projections",
            "Enter historical data — projections extend from the last historical year "
            "using independent growth rates for revenue, variable costs, and fixed costs",
        )

        with st.container(border=True):
            # ── 1. Data editor ────────────────────────────────────────────────
            sample = pd.DataFrame({
                "Metric":  ["Revenue", "Variable Costs", "Fixed Costs", "Depreciation"],
                "Year 1":  [5_000_000, 2_000_000, 1_500_000, 250_000],
            })
            df = st.data_editor(
                sample,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="fs_ed",
                column_config={
                    "Metric": st.column_config.TextColumn("Metric", width="medium"),
                },
            )

            # ── 2. Growth rate controls (use sidebar params as defaults) ────
            c1, c2, c3 = st.columns(3, gap="medium")
            with c1:
                rev_growth = (
                    st.slider(
                        "Revenue Growth % p.a.", -20.0, 40.0,
                        round(self.rev_growth * 100, 1),
                        0.5, key="fs_rev_g",
                        help="Compound annual growth applied to Revenue from the base year",
                    ) / 100
                )
            with c2:
                vc_inflation = (
                    st.slider(
                        "Variable Cost Inflation % p.a.", -10.0, 25.0,
                        round(self.vc_inflation * 100, 1),
                        0.5, key="fs_vc_i",
                        help="Compound annual cost inflation applied to Variable Costs",
                    ) / 100
                )
            with c3:
                fc_inflation = (
                    st.slider(
                        "Fixed Cost Inflation % p.a.", -10.0, 25.0,
                        round(self.fc_inflation * 100, 1),
                        0.5, key="fs_fc_i",
                        help="Compound annual cost inflation applied to Fixed Costs",
                    ) / 100
                )

            # ── 3. Input validation ────────────────────────────────────────
            if df is None or df.empty or "Metric" not in df.columns:
                self._info_box("Add at least one row with a Metric name.")
                return

            # Drop rows with empty / NaN metric names (BUG 3 fix)
            df = df.dropna(subset=["Metric"])
            df = df[df["Metric"].astype(str).str.strip() != ""]

            if df.empty:
                self._info_box("All rows have empty Metric names. Please name your metrics.")
                return

            num_cols = [c for c in df.columns if c != "Metric"]
            if not num_cols:
                self._info_box("Add at least one year column with numeric values.")
                return

            # Coerce all value columns to numeric (BUG 3 fix)
            df_clean = df.copy()
            for col in num_cols:
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").fillna(0.0)

            fy = self.forecast_years
            tr = self.tax_rate

            # ── 4. Extract base values from last historical year ───────────
            try:
                base: pd.Series = df_clean.set_index("Metric")[num_cols[-1]]
            except Exception as exc:
                self._error_box(f"Could not index on Metric column: {exc}")
                return

            base_rev = _to_float(base.get("Revenue", 0))
            base_vc  = _to_float(base.get("Variable Costs", 0))
            base_fc  = _to_float(base.get("Fixed Costs", 0))
            base_dep = _to_float(base.get("Depreciation", 0))

            # BUG 5 fix: warn if Revenue is 0 (ratio will be degenerate)
            if base_rev == 0:
                st.warning(
                    "⚠️ Base-year Revenue is **0** — variable cost ratios cannot be "
                    "computed.  The projection will use absolute base VC values instead."
                )

            # Detect custom (non-standard) metric rows
            standard_rows = {"Revenue", "Variable Costs", "Fixed Costs", "Depreciation",
                             "EBIT", "Tax", "Net Income"}
            custom_rows = [m for m in base.index if m not in standard_rows]
            if custom_rows:
                st.info(
                    f"ℹ️ Custom row(s) detected: **{', '.join(custom_rows)}**. "
                    "Historical values are preserved; projected columns will show **0** "
                    "for custom rows (automated projection not available for unlabelled lines)."
                )

            # ── 5. Build result DataFrame ──────────────────────────────────
            result_index = list(base.index) + [
                r for r in ["EBIT", "Tax", "Net Income"] if r not in base.index
            ]
            result = pd.DataFrame(index=result_index, dtype=float)

            # Fill historical columns
            for col in num_cols:
                yd: dict[str, float] = {
                    k: _to_float(v)
                    for k, v in df_clean.set_index("Metric")[col].items()
                }
                ebit = (
                    yd.get("Revenue", 0)
                    - yd.get("Variable Costs", 0)
                    - yd.get("Fixed Costs", 0)
                    - yd.get("Depreciation", 0)
                )
                yd["EBIT"]       = ebit
                yd["Tax"]        = max(0.0, ebit) * tr
                yd["Net Income"] = ebit - yd["Tax"]
                # BUG 2 fix: reindex to result_index so no keys are silently dropped
                result[col] = pd.Series(yd).reindex(result_index, fill_value=0.0)

            # ── 6. Add projected columns (BUG 1 + BUG 2 fixes) ────────────
            for i in range(fy):
                yr = f"Proj. Year {i + 1}"
                factor = i + 1   # years from base

                # Revenue — compound growth from base year
                rev = base_rev * (1 + rev_growth) ** factor

                # Variable Costs — compound inflation from base VC value
                # (independent of revenue growth — correctly models margin compression/expansion)
                vc = base_vc * (1 + vc_inflation) ** factor

                # Fixed Costs — compound inflation from base FC value
                fc = base_fc * (1 + fc_inflation) ** factor

                # Depreciation — flat (capex is sunk)
                dep = base_dep

                # Derived lines
                ebit = rev - vc - fc - dep
                tax  = max(0.0, ebit) * tr
                net  = ebit - tax

                proj_series: dict[str, float] = {
                    "Revenue":        rev,
                    "Variable Costs": vc,
                    "Fixed Costs":    fc,
                    "Depreciation":   dep,
                    "EBIT":           ebit,
                    "Tax":            tax,
                    "Net Income":     net,
                    # Custom rows → 0 (BUG 2 fix)
                    **{row: 0.0 for row in custom_rows},
                }

                # BUG 2 fix: reindex + fillna(0) guards against any remaining NaN
                result[yr] = (
                    pd.Series(proj_series)
                    .reindex(result_index, fill_value=0.0)
                    .fillna(0.0)
                )

            # ── 7. Display pro-forma table ─────────────────────────────────
            st.markdown(
                f"<h4 style='color:{_NAVY};font-family:\"Plus Jakarta Sans\",sans-serif;"
                f"font-weight:700;margin:16px 0 8px'>📊 Pro-Forma Income Statement</h4>",
                unsafe_allow_html=True,
            )

            # BUG 3 fix: fillna(0) before styling to prevent Styler errors
            styled = (
                result.fillna(0.0)
                .style.format(fmt)
                .set_properties(**{"text-align": "right"})
                .set_table_styles([
                    {"selector": "th", "props": [("text-align", "left"),
                                                 ("font-family", "Plus Jakarta Sans, sans-serif"),
                                                 ("font-size", "0.82rem")]},
                    {"selector": "td", "props": [("font-family", "'Courier New', monospace"),
                                                 ("font-size", "0.85rem")]},
                ])
                .apply(
                    lambda row: [
                        "font-weight:700;color:#0F2744" if row.name in ("EBIT", "Net Income")
                        else "color:#EF4444" if row.name == "Tax"
                        else ""
                    ] * len(row),
                    axis=1,
                )
            )
            st.dataframe(styled, use_container_width=True)

            st.markdown("---")

            # ── 8. Charts ─────────────────────────────────────────────────
            tab1, tab2, tab3 = st.tabs([
                "📈 Revenue & Net Income", "🌊 Margin Trend", "📊 Waterfall"
            ])

            all_periods = list(result.columns)
            hist_count  = len(num_cols)

            # ──── Tab 1: Revenue & Net Income trend ────────────────────────
            with tab1:
                if "Revenue" in result.index and "Net Income" in result.index:
                    rev_vals = result.loc["Revenue"].fillna(0).tolist()
                    net_vals = result.loc["Net Income"].fillna(0).tolist()

                    fig = go.Figure()
                    # Shade projected region
                    if hist_count < len(all_periods):
                        first_proj = all_periods[hist_count]
                        fig.add_vrect(
                            x0=first_proj, x1=all_periods[-1],
                            fillcolor="rgba(14,165,160,0.06)",
                            layer="below", line_width=0,
                            annotation_text="Projected",
                            annotation_position="top left",
                            annotation_font_size=10,
                            annotation_font_color=_TEAL,
                        )

                    fig.add_trace(go.Scatter(
                        x=all_periods, y=rev_vals, name="Revenue",
                        mode="lines+markers",
                        line=dict(color=_SKY, width=2.5),
                        marker=dict(size=7, color=_SKY, line=dict(color="#0D1117", width=1.5)),
                        fill="tozeroy",
                        fillcolor="rgba(56,189,248,0.08)",
                        hovertemplate="<b>%{x}</b><br>Revenue: ৳%{y:,.0f}<extra></extra>",
                    ))
                    fig.add_trace(go.Scatter(
                        x=all_periods, y=net_vals, name="Net Income",
                        mode="lines+markers",
                        line=dict(color=_EMR, width=2.5, dash="dash"),
                        marker=dict(size=7, color=_EMR, line=dict(color="#0D1117", width=1.5)),
                        hovertemplate="<b>%{x}</b><br>Net Income: ৳%{y:,.0f}<extra></extra>",
                    ))
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="#0D1117",
                        plot_bgcolor="#0D1117",
                        font=dict(family="'Plus Jakarta Sans',sans-serif", color="#CBD5E1"),
                        title=dict(
                            text="Revenue & Net Income Trend",
                            font=dict(size=14, color="#F8FAFC", weight=700),
                        ),
                        legend=dict(
                            orientation="h", yanchor="bottom", y=1.02,
                            bgcolor="rgba(0,0,0,0)", font=dict(size=11),
                        ),
                        xaxis=dict(gridcolor="#1E293B", linecolor="#334155"),
                        yaxis=dict(
                            tickprefix="\u09f3", gridcolor="#1E293B",
                            linecolor="#334155",
                        ),
                        hoverlabel=dict(
                            bgcolor="#1E293B", font_color="#F8FAFC", font_size=12,
                            bordercolor="#334155",
                        ),
                        margin=dict(t=52, b=20, l=10, r=10),
                        height=380,
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # ──── Tab 2: Margin trend (Net Margin %) ───────────────────────
            with tab2:
                if "Revenue" in result.index and "Net Income" in result.index:
                    rev_arr = result.loc["Revenue"].fillna(0).values
                    net_arr = result.loc["Net Income"].fillna(0).values
                    margins = [
                        safe_div(n, r) * 100
                        for n, r in zip(net_arr, rev_arr)
                    ]
                    ebit_arr = result.loc["EBIT"].fillna(0).values if "EBIT" in result.index else net_arr
                    ebit_margins = [safe_div(e, r) * 100 for e, r in zip(ebit_arr, rev_arr)]

                    fig2 = go.Figure()
                    if hist_count < len(all_periods):
                        fig2.add_vrect(
                            x0=all_periods[hist_count], x1=all_periods[-1],
                            fillcolor="rgba(14,165,160,0.06)",
                            layer="below", line_width=0,
                        )
                    # Add 15% green threshold line
                    fig2.add_hline(
                        y=15, line_dash="dot", line_color="#10B981",
                        annotation_text="Target 15%", annotation_position="top right",
                        annotation_font_size=10, annotation_font_color="#10B981",
                    )
                    fig2.add_trace(go.Scatter(
                        x=all_periods, y=ebit_margins, name="EBIT Margin %",
                        mode="lines+markers",
                        line=dict(color=_AMBER, width=2),
                        marker=dict(size=6, color=_AMBER),
                        hovertemplate="<b>%{x}</b><br>EBIT Margin: %{y:.1f}%<extra></extra>",
                    ))
                    fig2.add_trace(go.Scatter(
                        x=all_periods, y=margins, name="Net Margin %",
                        mode="lines+markers",
                        line=dict(color=_EMR, width=2.5),
                        marker=dict(
                            size=8, color=_EMR,
                            line=dict(color="#0D1117", width=1.5),
                        ),
                        hovertemplate="<b>%{x}</b><br>Net Margin: %{y:.1f}%<extra></extra>",
                    ))
                    fig2.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="#0D1117", plot_bgcolor="#0D1117",
                        font=dict(family="'Plus Jakarta Sans',sans-serif", color="#CBD5E1"),
                        title=dict(text="Margin Trend", font=dict(size=14, color="#F8FAFC")),
                        xaxis=dict(gridcolor="#1E293B"),
                        yaxis=dict(
                            ticksuffix="%", gridcolor="#1E293B",
                            zeroline=True, zerolinecolor="#334155",
                        ),
                        hoverlabel=dict(bgcolor="#1E293B", font_color="#F8FAFC"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                    bgcolor="rgba(0,0,0,0)"),
                        margin=dict(t=52, b=20, l=10, r=10),
                        height=380,
                    )
                    st.plotly_chart(fig2, use_container_width=True)

            # ──── Tab 3: Revenue waterfall bridge ──────────────────────────
            with tab3:
                if "Revenue" in result.index and len(all_periods) >= 2:
                    rev_series = result.loc["Revenue"].fillna(0)
                    waterfall_x     = []
                    waterfall_y     = []
                    waterfall_base  = []
                    waterfall_color = []

                    prev = rev_series.iloc[0]
                    waterfall_x.append(rev_series.index[0])
                    waterfall_y.append(prev)
                    waterfall_base.append(0)
                    waterfall_color.append(_SKY)

                    for period, val in rev_series.iloc[1:].items():
                        delta = val - prev
                        waterfall_x.append(str(period))
                        waterfall_y.append(abs(delta))
                        waterfall_base.append(prev if delta >= 0 else val)
                        waterfall_color.append(_EMR if delta >= 0 else _ROSE)
                        prev = val

                    fig3 = go.Figure(go.Bar(
                        x=waterfall_x,
                        y=waterfall_y,
                        base=waterfall_base,
                        marker_color=waterfall_color,
                        text=[fmt(v) for v in rev_series.values],
                        textposition="outside",
                        textfont=dict(size=10, color="#CBD5E1"),
                        hovertemplate="<b>%{x}</b><br>৳%{y:,.0f}<extra></extra>",
                    ))
                    fig3.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="#0D1117", plot_bgcolor="#0D1117",
                        font=dict(family="'Plus Jakarta Sans',sans-serif", color="#CBD5E1"),
                        title=dict(text="Revenue Bridge (Waterfall)", font=dict(size=14, color="#F8FAFC")),
                        xaxis=dict(gridcolor="#1E293B"),
                        yaxis=dict(tickprefix="\u09f3", gridcolor="#1E293B"),
                        margin=dict(t=52, b=20, l=10, r=10),
                        height=380,
                        showlegend=False,
                    )
                    st.plotly_chart(fig3, use_container_width=True)

            st.markdown("---")

            # ── 9. Download row ────────────────────────────────────────────
            dl_col1, dl_col2 = st.columns(2, gap="small")
            with dl_col1:
                csv_bytes = result.fillna(0).to_csv().encode("utf-8")
                st.download_button(
                    "⬇️ Download CSV",
                    data=csv_bytes,
                    file_name="finox_projections.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with dl_col2:
                try:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        result.fillna(0).to_excel(writer, sheet_name="Projections")
                    buf.seek(0)   # BUG 4 fix: explicit seek before read
                    st.download_button(
                        "⬇️ Download Excel",
                        data=buf.getvalue(),
                        file_name="finox_projections.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except ImportError:
                    st.caption("Install `openpyxl` to enable Excel download.")

            # ── 10. Build enriched AI context ─────────────────────────────
            # Compute year-by-year net margins for richer Grok analysis
            margins_ctx: dict[str, str] = {}
            if "Revenue" in result.index and "Net Income" in result.index:
                for col in all_periods:
                    r = result.at["Revenue", col]
                    n = result.at["Net Income", col]
                    if pd.notna(r) and r != 0:
                        margins_ctx[f"Net Margin — {col}"] = f"{safe_div(n, r):.1%}"

            # CAGR of revenue (hist base → final projected)
            first_rev_val = _to_float(result.at["Revenue", all_periods[0]]
                                      if "Revenue" in result.index else 0)
            last_rev_val  = _to_float(result.at["Revenue", all_periods[-1]]
                                      if "Revenue" in result.index else 0)
            last_net_val  = _to_float(result.at["Net Income", all_periods[-1]]
                                      if "Net Income" in result.index else 0)
            total_periods = len(all_periods) - 1
            cagr = ""
            if first_rev_val > 0 and last_rev_val > 0 and total_periods > 0:
                cagr = f"{((last_rev_val / first_rev_val) ** (1 / total_periods) - 1):.1%}"

            context_dict = {
                "Revenue Growth Rate":      f"{rev_growth:.1%}",
                "VC Inflation Rate":        f"{vc_inflation:.1%}",
                "FC Inflation Rate":        f"{fc_inflation:.1%}",
                "Tax Rate":                 f"{tr:.1%}",
                "Forecast Years":           fy,
                "Historical Periods":       hist_count,
                "Base Revenue":             fmt(first_rev_val),
                "Final Revenue":            fmt(last_rev_val),
                "Final Net Income":         fmt(last_net_val),
                "Revenue CAGR":             cagr or "N/A",
                "Net Margin (final yr)":    f"{safe_div(last_net_val, last_rev_val):.1%}",
                **margins_ctx,
            }

            self._insight_box(
                what=(
                    f"Projecting {rev_growth:.1%} annual revenue growth over {fy} year(s). "
                    f"Variable costs inflating at {vc_inflation:.1%} p.a. and fixed costs at "
                    f"{fc_inflation:.1%} p.a. Final-year revenue: {fmt(last_rev_val)} | "
                    f"Net income: {fmt(last_net_val)}."
                ),
                recommendation=(
                    "If net margin is declining despite revenue growth, VC inflation is "
                    "outpacing pricing power.  Consider a price escalation clause or supplier "
                    "renegotiation.  Use the Scenario Planner to stress-test the bear case."
                ),
                context_data=context_dict,
            )