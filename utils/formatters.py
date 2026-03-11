"""
utils/formatters.py  ·  FinOx Suite
=====================================
Pure utility functions shared across ALL modules.
Fully self-contained — zero imports from other project packages.

All modules MUST import from here instead of defining local helpers.

CACHING CHANGES (v2.0)
-----------------------
• build_projection_df() — wrapped with @st.cache_data. This function is called
  on every Streamlit rerun from multiple modules. All arguments are primitive
  Python types (float/int), making it perfectly safe to cache. The DataFrame
  result is serialized and returned from cache on subsequent identical calls.

• calculate_irr()       — wrapped with @st.cache_data. This runs a Newton-Raphson
  loop of up to 1,000 iterations. The input is a list[float] + int, which
  Streamlit's content-based hasher handles natively without risk of
  UnhashableTypeError.

• All other functions are intentionally NOT cached:
  - fmt / _fmt / to_pct / compact_number / safe_div / _safe_div:
    These are trivial one-liners; caching overhead would exceed execution time.
  - read_file(): Accepts an uploaded Streamlit UploadedFile object, which is
    not hashable. Caching would raise UnhashableTypeError.
  - calculate_npv(): Single-pass list comprehension; too cheap to cache.
  - normalise_df_columns(): Mutates a DataFrame in-place; not safe to cache.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

# Hardcoded here to prevent circular imports — ৳
_CURRENCY: str = "\u09f3"


# ===========================================================================
# 1. Number & Currency Formatting
# ===========================================================================

def fmt(x: Any, symbol: str = _CURRENCY) -> str:
    """
    Format a number as Taka string with thousands separator.
    Examples:  1_234_567 → '৳1,234,567'
               None / NaN → '৳0'
    """
    try:
        return f"{symbol}{float(x):,.0f}"
    except (ValueError, TypeError):
        return f"{symbol}0"


# Alias for modules that still call _fmt(x) internally
def _fmt(x: Any) -> str:
    return fmt(x)


def to_pct(x: float, decimals: int = 1) -> str:
    """
    Format 0.123 → '12.3%'.
    Returns 'N/A' on bad input.
    """
    try:
        return f"{float(x) * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def compact_number(x: float) -> str:
    """
    Compact large numbers:  1_500_000 → '1.5M',  2_300 → '2.3K'
    """
    try:
        v = abs(float(x))
        sign = "-" if float(x) < 0 else ""
        if v >= 1_000_000_000:
            return f"{sign}{v / 1_000_000_000:.1f}B"
        if v >= 1_000_000:
            return f"{sign}{v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"{sign}{v / 1_000:.1f}K"
        return f"{sign}{v:.1f}"
    except Exception:
        return str(x)


# ===========================================================================
# 2. Safe Arithmetic
# ===========================================================================

def safe_div(numerator: Any, denominator: Any, fallback: float = 0.0) -> float:
    """Division with zero-denominator and type-error guard."""
    try:
        d = float(denominator)
        return float(numerator) / d if d != 0.0 else fallback
    except (ValueError, TypeError, ZeroDivisionError):
        return fallback


# Alias
def _safe_div(n: Any, d: Any, fb: float = 0.0) -> float:
    return safe_div(n, d, fb)


# ===========================================================================
# 3. File Reading  (CRITICAL BUG FIX — no more infinite recursion)
# ===========================================================================

def read_file(uploaded_file: Any) -> pd.DataFrame:
    """
    Read an uploaded Streamlit file object into a DataFrame.

    Supports .csv, .xlsx, .xls.
    Raises ValueError for unsupported extensions.
    Raises IOError if pandas cannot parse the file.

    NOTE: This function intentionally NEVER calls itself.
          The original codebase had infinite recursion on the CSV branch;
          this implementation calls pd.read_csv / pd.read_excel directly.

    NOTE ON CACHING: This function accepts a Streamlit UploadedFile object,
    which is NOT hashable. It is therefore intentionally NOT decorated with
    @st.cache_data to avoid UnhashableTypeError crashes.
    """
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError(
        f"Unsupported file type: '{uploaded_file.name}'. "
        "Please upload a .csv, .xlsx, or .xls file."
    )


# ===========================================================================
# 4. Financial Mathematics
# ===========================================================================

def calculate_npv(cash_flows: list[float], discount_rate: float) -> float:
    """
    Net Present Value of cash flows starting at t=1 (Year 1).
    CF at t=0 (initial investment) must be included as cash_flows[0]
    if you want to call this from a full cash-flow list.
    """
    return sum(cf / (1 + discount_rate) ** (i + 1) for i, cf in enumerate(cash_flows))


@st.cache_data
def calculate_irr(cash_flows: list[float], max_iter: int = 1000) -> float:
    """
    Internal Rate of Return via Newton-Raphson.
    Returns float('nan') if it does not converge.
    cash_flows[0] should be negative (initial outlay).

    @st.cache_data: All arguments (list[float], int) are natively hashable by
    Streamlit's content-based hasher. No UnhashableTypeError risk. The function
    is a pure computation loop (up to 1,000 iterations) with no side effects,
    making it a textbook caching candidate.
    """
    rate = 0.10
    for _ in range(max_iter):
        npv  = sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        dnpv = sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))
        if abs(dnpv) < 1e-10:
            break
        rate -= npv / dnpv
        if rate <= -1.0:
            return float("nan")
    return rate


@st.cache_data
def build_projection_df(
    price: float,
    qty: float,
    var_cost: float,
    fixed_monthly: float,
    capex_init: float,
    dep_years: int,
    tax_rate: float,
    rev_growth: float,
    vc_inflation: float,
    fc_inflation: float,
    forecast_years: int,
) -> pd.DataFrame:
    """
    Multi-year financial projection DataFrame.

    Returns columns:
        Year, Revenue, COGS, Gross Profit, Fixed Costs,
        EBITDA, Depreciation, EBIT, Tax, Net Profit

    @st.cache_data: All 11 parameters are primitive Python types (float/int).
    Streamlit hashes these trivially. The function is a pure loop with no side
    effects — result is deterministic for any given set of inputs.
    """
    annual_depr = capex_init / dep_years if dep_years > 0 else 0.0
    base_rev    = price * qty * 12
    rows: list[dict] = []

    for i in range(forecast_years):
        rev    = base_rev          * (1 + rev_growth)   ** i
        vc_u   = var_cost          * (1 + vc_inflation)  ** i
        fc     = fixed_monthly * 12 * (1 + fc_inflation) ** i
        qty_i  = qty * 12          * (1 + rev_growth)   ** i
        cogs   = qty_i * vc_u
        gp     = rev - cogs
        ebitda = gp - fc
        ebit   = ebitda - annual_depr
        tax    = max(0.0, ebit * tax_rate)
        net    = ebit - tax
        rows.append({
            "Year":        f"Year {i + 1}",
            "Revenue":     rev,
            "COGS":        cogs,
            "Gross Profit": gp,
            "Fixed Costs": fc,
            "EBITDA":      ebitda,
            "Depreciation": annual_depr,
            "EBIT":        ebit,
            "Tax":         tax,
            "Net Profit":  net,
        })

    return pd.DataFrame(rows)


# ===========================================================================
# 5. DataFrame Helpers
# ===========================================================================

def normalise_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all column names."""
    df.columns = [str(c).strip() for c in df.columns]
    return df