"""
config/settings.py  ·  FinOx Suite  (v4.0 — Gemini)
======================================================
Central configuration hub.

API Key Security
-----------------
All key resolution is delegated to config/api_keys.py, which
implements the priority chain:
    Streamlit Secrets → .env / Environment Variable → Fallback

To get a key anywhere in the codebase:
    from config.api_keys import get_gemini_key
    key = get_gemini_key()

Changelog v4.0
---------------
• Updated docstring and references from xAI → Gemini.
• GLOBAL_CSS Layer 20 added: fixes "Keyboard Double" / 
  keyboard_double_arrow_right tooltip artifact in the sidebar
  collapse button that appears as raw visible text in some 
  browser/OS combinations.
• All other layers (0–19) are unchanged from v3.1.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Brand & Theme
# ---------------------------------------------------------------------------

APP_TITLE       = "FinOx — Professional BI & Data Science Suite"
APP_ICON        = "🦊"
APP_LAYOUT      = "wide"
CURRENCY_SYMBOL = "\u09f3"   # ৳

BRAND_COLORS: dict[str, str] = {
    "primary":    "#0F2744",
    "secondary":  "#0EA5A0",
    "accent":     "#3B82F6",
    "success":    "#10B981",
    "warning":    "#F59E0B",
    "danger":     "#EF4444",
    "neutral":    "#94A3B8",
    "bg":         "#F1F5F9",
    "card":       "#FFFFFF",
    "border":     "#E2E8F0",
    "dark_bg":    "#0D1117",
    "dark_card":  "#161B22",
    "dark_border":"#30363D",
}

# ---------------------------------------------------------------------------
# Plotly Templates & Palettes
# ---------------------------------------------------------------------------

PLOTLY_TEMPLATE      = "plotly_white"
PLOTLY_DARK_TEMPLATE = "plotly_dark"

CHART_PALETTE: list[str] = [
    "#3B82F6", "#0EA5A0", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#14B8A6", "#64748B",
]

CHART_PALETTE_DARK: list[str] = [
    "#38BDF8",   # sky blue
    "#34D399",   # emerald
    "#FB923C",   # amber-orange
    "#F87171",   # rose
    "#A78BFA",   # violet
    "#F472B6",   # pink
    "#22D3EE",   # cyan
    "#94A3B8",   # slate
]


# ---------------------------------------------------------------------------
# Global CSS — injected once at startup via app.py
# ---------------------------------------------------------------------------

GLOBAL_CSS = """
<style>
    /* ══════════════════════════════════════════════════════════════════════
       LAYER 0 — Font import
       ══════════════════════════════════════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 1 — CSS custom properties (design tokens)
       ══════════════════════════════════════════════════════════════════════ */
    :root {
        --font-primary:  'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', sans-serif;
        --color-navy:    #0F2744;
        --color-teal:    #0EA5A0;
        --color-accent:  #3B82F6;
        --color-bg:      #F1F5F9;
        --color-card:    #FFFFFF;
        --color-border:  #E2E8F0;
        --color-text:    #1E293B;
        --color-muted:   #64748B;

        --shadow-sm:  0 1px 3px rgba(15,39,68,0.06), 0 1px 2px rgba(15,39,68,0.04);
        --shadow-md:  0 4px 12px rgba(15,39,68,0.08), 0 2px 4px rgba(15,39,68,0.04);
        --shadow-lg:  0 8px 32px rgba(15,39,68,0.13), 0 4px 10px rgba(15,39,68,0.07);
        --shadow-xl:  0 16px 48px rgba(15,39,68,0.16), 0 8px 16px rgba(15,39,68,0.08);

        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 16px;
        --radius-xl: 24px;
        --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

        /* z-index scale */
        --z-base:    0;
        --z-card:    10;
        --z-sticky:  100;
        --z-tooltip: 400;
        --z-modal:   600;
        --z-top:     900;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 2 — App shell
       ══════════════════════════════════════════════════════════════════════ */
    .stApp {
        background-color: var(--color-bg);
        font-family: var(--font-primary);
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 3 — Global typography
       ══════════════════════════════════════════════════════════════════════ */
    body, p, span, div, label, input, textarea, select,
    [data-testid="stMarkdownContainer"] {
        font-family: var(--font-primary) !important;
        color: var(--color-text);
        word-break: break-word;
        overflow-wrap: break-word;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-primary) !important;
        color: var(--color-navy);
        line-height: 1.3;
        letter-spacing: -0.3px;
        font-weight: 700;
        overflow: hidden;
        text-overflow: ellipsis;
        word-break: break-word;
    }
    h1 { font-size: 2rem;    font-weight: 800; }
    h2 { font-size: 1.6rem;  font-weight: 700; }
    h3 { font-size: 1.25rem; font-weight: 600; }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 4 — Page header utility
       ══════════════════════════════════════════════════════════════════════ */
    .main-header {
        font-size: 2.1rem;
        color: var(--color-navy);
        font-weight: 800;
        text-align: center;
        margin-bottom: 2rem;
        letter-spacing: -0.5px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 5 — Metric / KPI cards  (text-overwrite fix)
       ══════════════════════════════════════════════════════════════════════ */
    [data-testid="stMetric"] {
        background: var(--color-card);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 18px 20px;
        box-shadow: var(--shadow-sm);
        transition: var(--transition);
        position: relative;
        z-index: var(--z-card);
        overflow: hidden;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
        z-index: calc(var(--z-card) + 1);
    }
    [data-testid="stMetricLabel"]  { order: 0; flex-shrink: 0; }
    [data-testid="stMetricLabel"] > div {
        font-family: var(--font-primary) !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
        color: var(--color-muted) !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    [data-testid="stMetricValue"]  { order: 1; flex-shrink: 0; margin-top: 4px; }
    [data-testid="stMetricValue"] > div {
        font-family: var(--font-primary) !important;
        font-weight: 700 !important;
        color: var(--color-navy) !important;
        position: relative !important;
        white-space: normal;
        word-break: break-all;
        line-height: 1.3;
    }
    [data-testid="stMetricDelta"]  { order: 2; flex-shrink: 0; margin-top: 4px; }
    [data-testid="stMetricDelta"] > div {
        font-family: var(--font-primary) !important;
        font-size: 0.8rem !important;
        white-space: nowrap;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 6 — Dashboard grid helpers (.fnx-grid / .fnx-kpi-card)
       ══════════════════════════════════════════════════════════════════════ */
    .fnx-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        width: 100%;
        margin: 12px 0;
        position: relative;
        z-index: var(--z-base);
    }
    .fnx-kpi-card {
        flex: 1 1 180px;
        max-width: 280px;
        background: var(--color-card);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 18px 20px;
        box-shadow: var(--shadow-sm);
        position: relative;
        z-index: var(--z-card);
        overflow: hidden;
        min-height: 88px;
        transition: var(--transition);
    }
    .fnx-kpi-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
    .fnx-kpi-label {
        font-size: 0.70rem; font-weight: 700;
        color: var(--color-muted); text-transform: uppercase;
        letter-spacing: 0.8px; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; margin: 0 0 6px;
    }
    .fnx-kpi-value {
        font-size: 1.45rem; font-weight: 800;
        color: var(--color-navy); line-height: 1.2;
        word-break: break-all; overflow-wrap: anywhere;
    }
    .fnx-kpi-delta { font-size: 0.78rem; margin-top: 4px; white-space: nowrap; }
    .fnx-kpi-delta.positive { color: #10B981; }
    .fnx-kpi-delta.negative { color: #EF4444; }
    .fnx-kpi-accent {
        position: absolute; bottom: 0; left: 0;
        width: 100%; height: 3px;
        border-radius: 0 0 var(--radius-md) var(--radius-md);
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 7 — Glassmorphism card (auth page hero / featured sections)
       ══════════════════════════════════════════════════════════════════════ */
    .fnx-glass-card {
        background: rgba(255, 255, 255, 0.82);
        -webkit-backdrop-filter: blur(20px) saturate(160%);
        backdrop-filter: blur(20px) saturate(160%);
        border: 1px solid rgba(255, 255, 255, 0.55);
        border-radius: var(--radius-xl);
        box-shadow: var(--shadow-xl);
        padding: 40px 44px;
        position: relative;
        z-index: var(--z-card);
        overflow: hidden;
    }
    .fnx-glass-card::before {
        content: '';
        position: absolute; top: -60px; right: -60px;
        width: 200px; height: 200px;
        background: radial-gradient(circle, rgba(14,165,160,0.12) 0%, transparent 70%);
        pointer-events: none; z-index: 0;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 8 — Insight / callout box
       ══════════════════════════════════════════════════════════════════════ */
    .insight-box {
        background: linear-gradient(135deg, #EFF6FF 0%, #F0FDFA 100%);
        border: 1px solid rgba(14, 165, 160, 0.25);
        border-left: 4px solid var(--color-teal);
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        padding: 1.1rem 1.4rem;
        margin-top: 0.75rem;
        box-shadow: var(--shadow-sm);
        position: relative;
        z-index: var(--z-card);
        overflow: hidden;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 9 — Buttons
       ══════════════════════════════════════════════════════════════════════ */
    .stButton > button {
        font-family: var(--font-primary) !important;
        font-weight: 600 !important;
        letter-spacing: 0.1px;
        border-radius: var(--radius-sm) !important;
        transition: var(--transition) !important;
        position: relative;
        z-index: var(--z-card);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--color-navy), #1e4080) !important;
        border: none !important;
        box-shadow: var(--shadow-sm) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: var(--shadow-md) !important;
        transform: translateY(-1px) !important;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 10 — Tabs
       ══════════════════════════════════════════════════════════════════════ */
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-family: var(--font-primary) !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 11 — Input fields
       ══════════════════════════════════════════════════════════════════════ */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] select {
        font-family: var(--font-primary) !important;
        border-radius: var(--radius-sm) !important;
        border-color: var(--color-border) !important;
        transition: var(--transition) !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: var(--color-accent) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12) !important;
        position: relative;
        z-index: var(--z-tooltip);
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 12 — Sidebar user badge
       ══════════════════════════════════════════════════════════════════════ */
    .user-badge {
        background: linear-gradient(135deg, var(--color-navy) 0%, #0D3461 100%);
        color: #FFF;
        border-radius: var(--radius-md);
        padding: 12px 14px;
        margin-bottom: 10px;
        font-size: 0.82rem;
        border: 1px solid rgba(255,255,255,0.07);
        box-shadow: var(--shadow-sm);
        overflow: hidden;
        word-break: break-word;
    }
    .user-badge strong {
        display: block; font-size: 0.9rem; font-weight: 700;
        margin-bottom: 2px; font-family: var(--font-primary);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .user-badge code {
        font-size: 0.72rem;
        background: rgba(255,255,255,0.12);
        border-radius: 4px; padding: 2px 8px;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 13 — Plotly chart containers + tooltip z-index elevation
       ══════════════════════════════════════════════════════════════════════ */
    [data-testid="stPlotlyChart"] {
        border-radius: var(--radius-md);
        overflow: hidden;
        position: relative;
        z-index: var(--z-base);
    }
    .plotly .modebar,
    .plotly .modebar-container { z-index: var(--z-tooltip) !important; }
    .plotly .hoverlayer          { z-index: var(--z-tooltip) !important; }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 14 — Streamlit component fixes
       ══════════════════════════════════════════════════════════════════════ */
    [data-testid="stExpander"] {
        border: 1px solid var(--color-border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-sm) !important;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] {
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 15 — Welcome card
       ══════════════════════════════════════════════════════════════════════ */
    .welcome-card { text-align: center; padding: 48px 40px; overflow: hidden; }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 16 — Divider
       ══════════════════════════════════════════════════════════════════════ */
    hr {
        border: none;
        border-top: 1px solid var(--color-border);
        margin: 1.5rem 0;
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 17 — Footer
       ══════════════════════════════════════════════════════════════════════ */
    .footer-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        padding: 1.25rem 2rem;
        color: var(--color-muted);
        font-size: 0.85em;
        font-family: var(--font-primary);
        border-top: 1px solid var(--color-border);
        margin-top: 2.5rem;
        background: var(--color-card);
        border-radius: var(--radius-md) var(--radius-md) 0 0;
    }
    .footer-right a {
        color: var(--color-muted); margin-left: 16px;
        text-decoration: none; transition: var(--transition);
    }
    .footer-right a:hover { color: var(--color-navy); }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 18 — Mobile responsive
       ══════════════════════════════════════════════════════════════════════ */
    @media (max-width: 768px) {
        .main-header  { font-size: 1.7rem; white-space: normal; }
        .footer-container { flex-direction: column; text-align: center; }
        .footer-right { margin-top: 0; }
        .fnx-kpi-card { flex: 1 1 140px; }
        .fnx-glass-card { padding: 28px 22px; }
        :root { --font-primary: 'Plus Jakarta Sans', sans-serif; }
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 19 — Status badge utilities
       ══════════════════════════════════════════════════════════════════════ */
    .fnx-badge-pill {
        display: inline-flex; align-items: center; gap: 5px;
        font-size: 0.64rem; font-weight: 700;
        padding: 3px 10px; border-radius: 20px;
        letter-spacing: 0.5px; text-transform: uppercase;
        white-space: nowrap; line-height: 1.4;
    }
    .fnx-badge-success { background: #D1FAE5; color: #065F46; }
    .fnx-badge-warning { background: #FEF3C7; color: #92400E; }
    .fnx-badge-danger  { background: #FEE2E2; color: #991B1B; }
    .fnx-badge-info    { background: #DBEAFE; color: #1E40AF; }
    .fnx-badge-neutral { background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }
    .fnx-badge-live {
        background: linear-gradient(90deg, #0F2744, #0EA5A0);
        color: #FFF;
        box-shadow: 0 2px 8px rgba(14,165,160,0.25);
    }

    /* ══════════════════════════════════════════════════════════════════════
       LAYER 20 — Sidebar collapse-button "Keyboard Double" artifact fix
       ══════════════════════════════════════════════════════════════════════
       Root cause: Streamlit injects a Material Icon ligature string
       ("keyboard_double_arrow_right" / "keyboard_double_arrow_left")
       as a text node inside the sidebar collapse <button>.  In certain
       browser/OS/font combinations this ligature fails to render as an
       icon and instead appears as plain visible text in the sidebar.

       Fix strategy — four progressive layers of hiding:
         1. Target the specific aria-label / title attribute values.
         2. Hide all child <span> elements inside the collapse button.
         3. Clip the button container with overflow:hidden so any
            stray text node that escapes selector matching is clipped.
         4. Kill material-icon font-family text nodes that match the
            known ligature class names Streamlit uses.
       ══════════════════════════════════════════════════════════════════════ */

    /* — Fix 1: aria-label / title attribute selectors — */
    [aria-label="keyboard_double_arrow_right"],
    [aria-label="keyboard_double_arrow_left"],
    [title="keyboard_double_arrow_right"],
    [title="keyboard_double_arrow_left"] {
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
        pointer-events: none !important;
        overflow: hidden !important;
    }

    /* — Fix 2: span children of the collapsed-control button — */
    [data-testid="collapsedControl"] > span,
    [data-testid="collapsedControl"] span,
    [data-testid="stSidebarCollapsedControl"] span,
    button[data-testid="baseButton-headerNoPadding"] > span {
        font-size: 0 !important;
        color: transparent !important;
        line-height: 0 !important;
        visibility: hidden !important;
        display: inline-block !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }

    /* — Fix 3: clip the collapse button container — */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        overflow: hidden !important;
    }
    [data-testid="stSidebar"] [data-testid="baseButton-header"],
    [data-testid="stSidebar"] [data-testid="baseButton-headerNoPadding"] {
        overflow: hidden !important;
    }

    /* — Fix 4: material-icon / material-symbols class names — */
    .sidebar-collapse-control .material-icons,
    .sidebar-collapse-control .material-symbols-rounded,
    [data-testid="stSidebarNav"] ~ div > button span.material-icons,
    [data-testid="stSidebarNav"] ~ div > button span.material-symbols-rounded,
    button[aria-label*="keyboard_double"] span,
    button[title*="keyboard_double"] span {
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        display: none !important;
    }

</style>
"""


# ---------------------------------------------------------------------------
# Default sidebar / global financial parameters
# ---------------------------------------------------------------------------

DEFAULT_PARAMS: dict = {
    "price":           500.0,
    "qty":             1000.0,
    "var_cost":        200.0,
    "fixed_monthly":   150_000.0,
    "capex_init":      2_500_000.0,
    "forecast_years":  5,
    "dep_years":       7,
    "tax_rate":        0.25,
    "rev_growth":      0.10,
    "vc_inflation":    0.03,
    "fc_inflation":    0.05,
    "discount_rate":   0.12,
    "api_key":         "",
    "ai_provider":     "",
}


# ---------------------------------------------------------------------------
# Module registry
# ---------------------------------------------------------------------------

MODULE_REGISTRY: dict[str, dict] = {
    "🏠 Home":                 {"module": "modules.home",                "class": "HomeModule"},
    "📊 A/B Test":             {"module": "modules.ab_test",             "class": "ABTestModule"},
    "❗ Anomaly Detection":    {"module": "modules.anomaly_detection",   "class": "AnomalyDetectionModule"},
    "⭐ BCG Matrix":           {"module": "modules.product_portfolio",   "class": "ProductPortfolioModule"},
    "🌊 Capital Flow":         {"module": "modules.capital_flow",        "class": "CapitalFlowModule"},
    "🎯 Competitor Analysis":  {"module": "modules.competitor_analysis", "class": "CompetitorAnalysisModule"},
    "👥 Customer Analytics":   {"module": "modules.customer_analytics",  "class": "CustomerAnalyticsModule"},
    "💔 Churn Predictor":      {"module": "modules.churn_predictor",     "class": "ChurnPredictorModule"},
    "📑 Financial Statements": {"module": "modules.financial_statements","class": "FinancialStatementsModule"},
    "🔮 Forecasting":          {"module": "modules.forecasting",         "class": "ForecastingModule"},
    "🗺️ Geo Analytics":        {"module": "modules.geo_analytics",       "class": "GeoAnalyticsModule"},
    "👨‍💼 HR Analytics":         {"module": "modules.hr_analytics",        "class": "HRAnalyticsModule"},
    "📦 Inventory":            {"module": "modules.inventory",           "class": "InventoryModule"},
    "📢 Marketing ROI":        {"module": "modules.marketing_roi",       "class": "MarketingROIModule"},
    "🎲 Monte Carlo":          {"module": "modules.monte_carlo",         "class": "MonteCarloModule"},
    "🎭 Scenario Planner":     {"module": "modules.scenario_planner",    "class": "ScenarioPlannerModule"},
}


# ---------------------------------------------------------------------------
# Footer HTML
# ---------------------------------------------------------------------------

FOOTER_HTML = """
<link rel="stylesheet"
  href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.1/css/all.min.css">
<div class="footer-container">
    <div class="footer-left">
        <p>🦊 &copy; 2025 <strong>FinOx Suite</strong> — Developed by <strong>Sourab Dey Soptom</strong></p>
    </div>
    <div class="footer-right">
        <a href="https://www.linkedin.com/in/soptom/" target="_blank" title="LinkedIn">
            <i class="fab fa-linkedin fa-lg"></i>
        </a>
        <a href="https://github.com/soptom" target="_blank" title="GitHub">
            <i class="fab fa-github fa-lg"></i>
        </a>
    </div>
</div>
"""