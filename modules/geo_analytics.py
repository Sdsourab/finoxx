"""
modules/geo_analytics.py  ·  FinOx Suite  v3.0
================================================
Advanced Geospatial Intelligence Suite — Predictive & Prescriptive Edition.

New in v3.0
-----------
• Dynamic column mapping  — no hard-coded COLS list; user maps their own headers
• Auto-geocoding          — geopy Nominatim fills missing Lat/Lon automatically
• 3-D Hexagon Map         — pydeck HexagonLayer with 55° pitch, plasma gradient
• Density Heatmap         — px.density_mapbox for hotspot / coldspot analysis
• K-Means segmentation    — scikit-learn KMeans → Golden / Emerging / Dead zones
• Cannibalization Risk    — pairwise Haversine distance with configurable threshold
• White-Space Gap         — corridor identification for expansion targeting
• McKinsey AI brief       — _insight_box() receives a rich flat context dict

ARCHITECTURE RULES (DO NOT MODIFY):
  • Inherits BaseModule without change — never touches base_module.py
  • context_data is ALWAYS a flat dict — never a list
  • All new deps imported lazily with try/except — app degrades gracefully
  • @st.cache_data used on every heavy function for lightning-fast re-renders
"""
from __future__ import annotations

import math
import pickle
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from core.base_module import BaseModule
from utils.formatters import fmt, read_file

# ── Optional heavy deps — imported lazily, module degrades if absent ─────────
try:
    import pydeck as pdk
    _PYDECK_OK = True
except ImportError:
    _PYDECK_OK = False

try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
    _GEOPY_OK = True
except ImportError:
    _GEOPY_OK = False

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_OK = True
except ImportError:
    _SKLEARN_OK = False


# ── Colour palette for K-Means zones ─────────────────────────────────────────
_ZONE_COLOURS: dict[str, str] = {
    "🥇 Golden Zone":   "#FFD700",
    "🌱 Emerging Zone": "#00C49F",
    "💀 Dead Zone":     "#FF4B4B",
}

# ── Default demo data (Bangladesh sales network) ─────────────────────────────
_DEMO_DATA: dict[str, list] = {
    "Region":           ["Central", "South-East", "North", "South-West",
                         "Central", "South-East", "North", "Central",
                         "East",    "West"],
    "City":             ["Dhaka", "Chittagong", "Sylhet", "Khulna",
                         "Gazipur", "Cox's Bazar", "Rangpur", "Narayanganj",
                         "Comilla", "Rajshahi"],
    "Latitude":         [23.8103, 22.3569, 24.8949, 22.8456,
                         23.9999, 21.4272, 25.7439, 23.6238,
                         23.4607, 24.3745],
    "Longitude":        [90.4125, 91.7832, 91.8687, 89.5694,
                         90.4203, 91.9703, 89.2517, 90.5000,
                         91.1809, 88.6042],
    "Product_Category": ["Electronics", "Apparel", "Groceries", "Electronics",
                         "Apparel", "Groceries", "Electronics", "Groceries",
                         "Apparel", "Electronics"],
    "Sales":            [1_200_000, 850_000, 450_000, 600_000,
                         750_000,   300_000, 350_000, 550_000,
                         420_000,   680_000],
    "Transactions":     [150, 120, 90, 85, 110, 80, 70, 130, 95, 115],
}


# =============================================================================
# Helper: Haversine distance (km) between two lat/lon points
# =============================================================================

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance in kilometres between two points
    on Earth using the Haversine formula.
    Pure Python — no external deps required.
    """
    R = 6_371.0  # Earth's mean radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =============================================================================
# Cached geocoding — runs once per unique city list per session
# =============================================================================

@st.cache_data(show_spinner="🌍 Geocoding cities …")
def _geocode_cities(
    cities: tuple[str, ...],
) -> dict[str, tuple[float | None, float | None]]:
    """
    Return {city: (lat, lon)} mapping via Nominatim (OpenStreetMap).
    Uses a 1-second rate limiter to respect OSM's fair-use policy.
    Falls back to (None, None) on any failure.

    Parameter is a *tuple* (not list) so Streamlit can hash it correctly.
    """
    results: dict[str, tuple[float | None, float | None]] = {}
    if not _GEOPY_OK:
        return {c: (None, None) for c in cities}

    geolocator = Nominatim(user_agent="finox_suite_geocoder_v3")
    geocode    = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    for city in cities:
        try:
            loc = geocode(city)
            results[city] = (loc.latitude, loc.longitude) if loc else (None, None)
        except Exception:
            results[city] = (None, None)
    return results


# =============================================================================
# Cached K-Means — keyed on feature-matrix bytes so re-uploads retrigger
# =============================================================================

@st.cache_data(show_spinner="🧠 Running K-Means clustering …")
def _run_kmeans(feature_bytes: bytes, n_clusters: int = 3) -> np.ndarray:
    """
    Fit KMeans on a StandardScaler-normalised feature matrix.
    feature_bytes = pickle.dumps(ndarray) — hashable by st.cache_data.
    Returns raw cluster labels as a 1-D ndarray.
    """
    X: np.ndarray = pickle.loads(feature_bytes)
    scaler = StandardScaler()
    Xs     = scaler.fit_transform(X)
    km     = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    km.fit(Xs)
    return km.labels_


# =============================================================================
# Cached spatial analytics — cannibalization + white-space
# =============================================================================

@st.cache_data(show_spinner="📐 Computing spatial analytics …")
def _compute_spatial_analytics(
    city_bytes:         bytes,
    cannibalization_km: float,
) -> dict[str, Any]:
    """
    Run Haversine cannibalization and white-space gap analysis.
    city_bytes = pickle.dumps(city_data_df) for stable hashing.

    Returns a dict with keys:
      "cannibal_pairs" → list[dict]   (City A, City B, Distance km)
      "gap_list"       → list[dict]   (City A, City B, Gap km, Mid Lat, Mid Lon)
    """
    city_data: pd.DataFrame = pickle.loads(city_bytes)

    # ── 1. Cannibalization risk — check all Golden Zone pairs ─────────────────
    golden = city_data[city_data["Zone"] == "🥇 Golden Zone"].reset_index(drop=True)
    cannibal_pairs: list[dict] = []
    for i in range(len(golden)):
        for j in range(i + 1, len(golden)):
            d = _haversine_km(
                golden.loc[i, "Latitude"],  golden.loc[i, "Longitude"],
                golden.loc[j, "Latitude"],  golden.loc[j, "Longitude"],
            )
            if d < cannibalization_km:
                cannibal_pairs.append({
                    "City A":      golden.loc[i, "City"],
                    "City B":      golden.loc[j, "City"],
                    "Distance km": round(d, 1),
                })

    # ── 2. White-space gap — all cities sorted by longitude east→west ─────────
    sorted_df = city_data.sort_values("Longitude").reset_index(drop=True)
    gap_list: list[dict] = []
    for i in range(len(sorted_df) - 1):
        ra = sorted_df.loc[i]
        rb = sorted_df.loc[i + 1]
        gap = _haversine_km(
            ra["Latitude"], ra["Longitude"],
            rb["Latitude"], rb["Longitude"],
        )
        gap_list.append({
            "City A":  ra["City"],
            "City B":  rb["City"],
            "Gap km":  round(gap, 1),
            "Mid Lat": round((ra["Latitude"]  + rb["Latitude"])  / 2, 4),
            "Mid Lon": round((ra["Longitude"] + rb["Longitude"]) / 2, 4),
        })

    gap_list.sort(key=lambda x: x["Gap km"], reverse=True)

    return {
        "cannibal_pairs": cannibal_pairs,
        "gap_list":       gap_list[:3],   # top-3 largest unserved corridors
    }


# =============================================================================
# Cached aggregation — avoids re-running groupby on every widget interaction
# =============================================================================

@st.cache_data(show_spinner=False)
def _aggregate_cached(serialised: bytes) -> pd.DataFrame:
    """GroupBy city-level aggregation, keyed on pickled DataFrame bytes."""
    df: pd.DataFrame = pickle.loads(serialised)
    return (
        df.groupby(["City", "Region", "Latitude", "Longitude"])
        .agg(Total_Sales=("Sales", "sum"), Total_Txns=("Transactions", "sum"))
        .reset_index()
    )


# =============================================================================
# Main Module
# =============================================================================

class GeoAnalyticsModule(BaseModule):
    """
    Enterprise-grade geospatial intelligence module for the FinOx Suite.
    Inherits BaseModule perfectly — no changes to base_module.py required.
    """

    PAGE_ICON  = "🗺️"
    PAGE_TITLE = "Geo Analytics"

    # -------------------------------------------------------------------------
    # Public entry point — called by app.py
    # -------------------------------------------------------------------------

    def render(self) -> None:
        self._page_header(
            "🗺️ Advanced Geospatial Intelligence Suite",
            (
                "Predictive market segmentation · "
                "Cannibalization risk · "
                "White-space expansion"
            ),
        )

        # ── Sidebar controls ─────────────────────────────────────────────────
        with st.sidebar:
            st.markdown("### ⚙️ Geo Analytics Controls")
            n_clusters         = st.slider("K-Means Clusters",          2, 6,   3)
            cannibalization_km = st.slider("Cannibalization Radius (km)", 10, 500, 50)
            heatmap_radius     = st.slider("Heatmap Radius",             5, 50,  20)

        with st.container(border=True):
            st.info(
                "Upload a CSV / Excel with columns for **City, Sales, Transactions, "
                "Region** (optional: Latitude, Longitude, Product_Category). "
                "Missing coordinates will be auto-geocoded via OpenStreetMap."
            )
            df, col_map = self._load()
            if df is None:
                return

        # Rename user columns → internal standard names
        rename_map = {v: k for k, v in col_map.items() if v and v != k}
        df = df.rename(columns=rename_map)

        # ── Auto-geocode if Lat/Lon are absent or partially missing ───────────
        df = self._ensure_coordinates(df)
        if df is None:
            return

        df_geo = df.dropna(subset=["Latitude", "Longitude"]).copy()
        if df_geo.empty:
            self._error_box("No valid coordinates found — cannot render maps.")
            return

        # ── City-level aggregation ────────────────────────────────────────────
        agg = _aggregate_cached(pickle.dumps(df_geo))

        # ── K-Means segmentation ──────────────────────────────────────────────
        agg = self._apply_kmeans(agg, n_clusters)

        # ── Spatial analytics ─────────────────────────────────────────────────
        spatial = _compute_spatial_analytics(pickle.dumps(agg), cannibalization_km)

        # ── Render all tabs ───────────────────────────────────────────────────
        tabs = st.tabs([
            "🧊 3D Hex Map",
            "🔥 Density Heatmap",
            "🎯 Market Segments",
            "⚠️ Cannibalization Risk",
            "🌍 White-Space Analysis",
            "📈 Regional Performance",
            "📦 Product Deep-Dive",
        ])

        with tabs[0]:
            self._tab_3d_hex(agg)
        with tabs[1]:
            self._tab_heatmap(agg, heatmap_radius)
        with tabs[2]:
            self._tab_segments(agg)
        with tabs[3]:
            self._tab_cannibalization(spatial["cannibal_pairs"], cannibalization_km)
        with tabs[4]:
            self._tab_whitespace(agg, spatial["gap_list"])
        with tabs[5]:
            self._tab_regional(df_geo)
        with tabs[6]:
            self._tab_product(df_geo)

        # ── McKinsey AI Insight — always last, full-page width ────────────────
        self._render_ai_insights(agg, spatial)

    # =========================================================================
    # Data loading & dynamic column mapping
    # =========================================================================

    def _load(self) -> tuple[pd.DataFrame | None, dict[str, str | None]]:
        """
        Renders a file uploader + dynamic column-mapping selectboxes.
        Returns (df, col_map) where col_map maps internal names → user column names.
        Falls back to the built-in demo data set if nothing is uploaded.
        """
        up = st.file_uploader(
            "Upload Sales CSV or Excel",
            type=["csv", "xlsx", "xls"],
            key="geo_up",
        )

        if up is not None:
            try:
                raw_df = read_file(up)
            except Exception as exc:
                self._error_box(f"Could not read file: {exc}")
                return None, {}

            st.success(
                f"✅ Loaded **{len(raw_df):,}** rows × **{len(raw_df.columns)}** columns"
            )

            # ── Dynamic column mapping ────────────────────────────────────────
            st.markdown("#### 🔗 Map Your Columns")
            cols_with_none = [None] + list(raw_df.columns)

            def _pick(label: str, hint: str, required: bool = True) -> str | None:
                """Auto-detect column by hint substring; user can override."""
                default = next(
                    (c for c in raw_df.columns if hint.lower() in str(c).lower()),
                    None,
                )
                idx    = cols_with_none.index(default) if default in cols_with_none else 0
                return st.selectbox(
                    f"{'★' if required else '◎'} {label}",
                    cols_with_none,
                    index=idx,
                    key=f"geo_col_{label}",
                )

            with st.expander("🗂️ Column Mapping (auto-detected — override if needed)",
                             expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    city_col   = _pick("City",             "city")
                    sales_col  = _pick("Sales",            "sales")
                    region_col = _pick("Region",           "region",   required=False)
                with c2:
                    txn_col    = _pick("Transactions",     "trans")
                    lat_col    = _pick("Latitude",         "lat",      required=False)
                with c3:
                    lon_col    = _pick("Longitude",        "lon",      required=False)
                    cat_col    = _pick("Product_Category", "product",  required=False)

            # Validate required mappings
            for label, val in [("City", city_col), ("Sales", sales_col),
                                ("Transactions", txn_col)]:
                if val is None:
                    self._error_box(f"Required column **{label}** is not mapped.")
                    return None, {}

            col_map: dict[str, str | None] = {
                "City":             city_col,
                "Sales":            sales_col,
                "Transactions":     txn_col,
                "Region":           region_col,
                "Latitude":         lat_col,
                "Longitude":        lon_col,
                "Product_Category": cat_col,
            }

            # Inject placeholder columns for unmapped optional fields
            if region_col is None:
                raw_df["Region"]           = "Unknown"
                col_map["Region"]          = "Region"
            if cat_col is None:
                raw_df["Product_Category"] = "Unknown"
                col_map["Product_Category"] = "Product_Category"

            return raw_df, col_map

        # ── Demo data fallback ────────────────────────────────────────────────
        self._info_box(
            "No file uploaded — using the built-in Bangladesh demo dataset. "
            "Upload your own CSV / Excel above to analyse real data."
        )
        demo_df = pd.DataFrame(_DEMO_DATA)
        col_map = {k: k for k in demo_df.columns}
        return demo_df, col_map

    # =========================================================================
    # Auto-geocoding
    # =========================================================================

    def _ensure_coordinates(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """
        Ensures Latitude and Longitude columns exist and are numeric.
        For any rows where coordinates are missing, attempts auto-geocoding
        via geopy Nominatim.  Warns if geopy is not installed.
        """
        # Create columns if they don't exist at all
        if "Latitude" not in df.columns:
            df["Latitude"]  = float("nan")
        if "Longitude" not in df.columns:
            df["Longitude"] = float("nan")

        df["Latitude"]  = pd.to_numeric(df["Latitude"],  errors="coerce")
        df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

        missing_mask = df["Latitude"].isna() | df["Longitude"].isna()
        if not missing_mask.any():
            return df

        cities_to_geocode = tuple(df.loc[missing_mask, "City"].unique())

        if not _GEOPY_OK:
            st.warning(
                "⚠️ **geopy** is not installed — cannot auto-geocode missing coordinates. "
                "Run `pip install geopy` **or** include Latitude/Longitude in your file."
            )
            return df

        geo_map = _geocode_cities(cities_to_geocode)
        for city, (lat, lon) in geo_map.items():
            mask = (df["City"] == city) & missing_mask
            df.loc[mask, "Latitude"]  = lat
            df.loc[mask, "Longitude"] = lon

        still_missing = (df["Latitude"].isna() | df["Longitude"].isna()).sum()
        if still_missing:
            st.warning(
                f"⚠️ {still_missing} row(s) still lack coordinates after geocoding "
                "and will be excluded from map views."
            )

        return df

    # =========================================================================
    # K-Means segmentation
    # =========================================================================

    def _apply_kmeans(self, agg: pd.DataFrame, n_clusters: int) -> pd.DataFrame:
        """
        Fits KMeans on [Total_Sales, Total_Txns, Latitude, Longitude],
        then relabels clusters by descending mean sales into human-readable zones.
        Adds 'Zone' and 'Zone_Colour' columns to the aggregated DataFrame.
        """
        if not _SKLEARN_OK:
            agg["Zone"]        = "🌱 Emerging Zone"
            agg["Zone_Colour"] = _ZONE_COLOURS["🌱 Emerging Zone"]
            st.warning(
                "⚠️ scikit-learn not installed — K-Means skipped. "
                "Run `pip install scikit-learn`."
            )
            return agg

        try:
            X      = agg[["Total_Sales", "Total_Txns", "Latitude", "Longitude"]].values
            labels = _run_kmeans(pickle.dumps(X), n_clusters)
            agg    = agg.copy()
            agg["_cluster"] = labels

            # Rank clusters by mean Total_Sales → assign zone names
            cluster_means = (
                agg.groupby("_cluster")["Total_Sales"]
                .mean()
                .sort_values(ascending=False)
                .reset_index()
            )

            # Build enough zone names for however many clusters were requested
            _zone_names = ["🥇 Golden Zone", "🌱 Emerging Zone", "💀 Dead Zone"]
            while len(_zone_names) < n_clusters:
                _zone_names.append(f"📊 Zone {len(_zone_names) + 1}")

            _zone_colours_ext = {**_ZONE_COLOURS}
            for extra in _zone_names[3:]:
                _zone_colours_ext[extra] = "#A0A0A0"

            cluster_means["Zone"] = _zone_names[:n_clusters]
            cluster_map = cluster_means.set_index("_cluster")["Zone"].to_dict()

            agg["Zone"]        = agg["_cluster"].map(cluster_map)
            agg["Zone_Colour"] = agg["Zone"].map(
                lambda z: _zone_colours_ext.get(z, "#A0A0A0")
            )
            agg.drop(columns=["_cluster"], inplace=True)

        except Exception as exc:
            self._error_box(f"K-Means segmentation failed: {exc}")
            agg["Zone"]        = "🌱 Emerging Zone"
            agg["Zone_Colour"] = _ZONE_COLOURS["🌱 Emerging Zone"]

        return agg

    # =========================================================================
    # Tab renderers
    # =========================================================================

    # ── Tab 1: 3-D Hexagon Map ─────────────────────────────────────────────────

    def _tab_3d_hex(self, agg: pd.DataFrame) -> None:
        """
        3-D HexagonLayer via pydeck with a 55° pitch.
        Falls back to px.scatter_mapbox if pydeck is not installed.
        """
        st.subheader("🧊 3D Hexagon Sales Map")

        if not _PYDECK_OK:
            st.info(
                "pydeck not installed — showing 2-D scatter fallback. "
                "Run `pip install pydeck` for the full 3-D experience."
            )
            fig = px.scatter_mapbox(
                agg,
                lat="Latitude",
                lon="Longitude",
                size="Total_Sales",
                color="Total_Sales",
                hover_name="City",
                color_continuous_scale="Plasma",
                zoom=5,
                height=520,
                mapbox_style="carto-positron",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Build pydeck map data — pydeck expects "lon"/"lat" column names
            map_data = agg[["Longitude", "Latitude", "Total_Sales", "Total_Txns"]].rename(
                columns={"Longitude": "lon", "Latitude": "lat"}
            )

            layer = pdk.Layer(
                "HexagonLayer",
                data=map_data,
                get_position=["lon", "lat"],
                get_elevation="Total_Sales",
                elevation_scale=0.0002,
                elevation_range=[0, 5000],
                radius=15_000,
                pickable=True,
                extruded=True,
                color_range=[
                    [26,  152, 80,  200],   # dark green  (low)
                    [102, 189, 99,  200],
                    [217, 239, 139, 200],
                    [254, 224, 139, 200],
                    [252, 141, 89,  200],
                    [215, 48,  39,  200],   # dark red    (high)
                ],
            )

            view = pdk.ViewState(
                latitude=agg["Latitude"].mean(),
                longitude=agg["Longitude"].mean(),
                zoom=6,
                pitch=55,
                bearing=-10,
            )

            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                map_style="mapbox://styles/mapbox/dark-v9",
                tooltip={"text": "Sales: {elevationValue}"},
            )
            st.pydeck_chart(deck, use_container_width=True)

        # KPI strip beneath the map
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cities Mapped",      f"{len(agg):,}")
        c2.metric("Total Sales",         fmt(agg["Total_Sales"].sum()))
        c3.metric("Total Transactions",  f"{int(agg['Total_Txns'].sum()):,}")
        top = agg.loc[agg["Total_Sales"].idxmax()]
        c4.metric("Top City",            str(top["City"]))

    # ── Tab 2: Density Heatmap ─────────────────────────────────────────────────

    def _tab_heatmap(self, agg: pd.DataFrame, radius: int) -> None:
        """Density heatmap weighted by Total_Sales + hotspot / coldspot cards."""
        st.subheader("🔥 Sales Density Heatmap — Hotspots & Coldspots")

        fig = px.density_mapbox(
            agg,
            lat="Latitude",
            lon="Longitude",
            z="Total_Sales",
            radius=radius,
            center={"lat": agg["Latitude"].mean(), "lon": agg["Longitude"].mean()},
            zoom=5,
            mapbox_style="carto-darkmatter",
            color_continuous_scale="Inferno",
            title="Revenue Density  (brighter = higher sales concentration)",
            height=540,
        )
        fig.update_layout(margin=dict(r=0, t=40, l=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Hotspot / Coldspot callout cards
        top3    = agg.nlargest(3, "Total_Sales")
        bottom3 = agg.nsmallest(3, "Total_Sales")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔥 Top 3 Hotspots")
            for _, row in top3.iterrows():
                st.success(
                    f"**{row['City']}** — {fmt(row['Total_Sales'])}  "
                    f"| {int(row['Total_Txns'])} txns"
                )
        with c2:
            st.markdown("#### 🧊 Top 3 Coldspots")
            for _, row in bottom3.iterrows():
                st.error(
                    f"**{row['City']}** — {fmt(row['Total_Sales'])}  "
                    f"| {int(row['Total_Txns'])} txns"
                )

    # ── Tab 3: Market Segments ─────────────────────────────────────────────────

    def _tab_segments(self, agg: pd.DataFrame) -> None:
        """K-Means zone summary cards, colour-coded scatter map, styled table."""
        st.subheader("🎯 Market Segmentation — K-Means Zones")

        if not _SKLEARN_OK:
            st.info("Install scikit-learn to enable K-Means market segmentation.")

        # One summary card per zone
        for zone, colour in _ZONE_COLOURS.items():
            subset = agg[agg["Zone"] == zone]
            if subset.empty:
                continue
            with st.container(border=True):
                ca, cb, cc = st.columns(3)
                ca.metric(zone,             f"{len(subset)} cities")
                cb.metric("Total Sales",     fmt(subset["Total_Sales"].sum()))
                cc.metric("Total Txns",      f"{int(subset['Total_Txns'].sum()):,}")

        # Colour-coded scatter map
        fig = px.scatter_mapbox(
            agg,
            lat="Latitude",
            lon="Longitude",
            color="Zone",
            color_discrete_map={z: c for z, c in _ZONE_COLOURS.items()},
            size="Total_Sales",
            hover_name="City",
            hover_data={
                "Total_Sales": ":,.0f",
                "Total_Txns":  True,
                "Zone":        True,
                "Latitude":    False,
                "Longitude":   False,
            },
            zoom=5,
            height=480,
            mapbox_style="carto-positron",
            title="City Zones — K-Means Spatial Segmentation",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Styled summary dataframe
        display_cols = [c for c in ["City", "Region", "Zone", "Total_Sales", "Total_Txns"]
                        if c in agg.columns]
        st.dataframe(
            agg[display_cols]
            .sort_values("Total_Sales", ascending=False)
            .style.format({"Total_Sales": fmt})
            .applymap(
                lambda z: f"color: {_ZONE_COLOURS.get(z, 'white')}; font-weight:bold",
                subset=["Zone"],
            ),
            hide_index=True,
            use_container_width=True,
        )

    # ── Tab 4: Cannibalization Risk ────────────────────────────────────────────

    def _tab_cannibalization(
        self,
        cannibal_pairs: list[dict],
        threshold_km:   float,
    ) -> None:
        """Alert banners + expandable pairwise distance matrix."""
        st.subheader("⚠️ Cannibalization Risk Analysis")
        st.caption(
            f"Golden Zone city pairs within **{threshold_km} km** of each other "
            "risk cannibalising one another's market share. "
            "Adjust the sidebar radius to change sensitivity."
        )

        if not cannibal_pairs:
            st.success(
                "✅ No cannibalization risk detected within the current radius. "
                "Your Golden Zone cities are well-separated geographically."
            )
        else:
            for pair in cannibal_pairs:
                st.error(
                    f"⚠️  **{pair['City A']}** ↔ **{pair['City B']}**  ·  "
                    f"Distance: **{pair['Distance km']} km**  "
                    f"(threshold: {threshold_km} km)"
                )

            with st.expander("📐 Full Pairwise Distance Matrix (Golden Zone cities)"):
                pairs_df = pd.DataFrame(cannibal_pairs)
                st.dataframe(
                    pairs_df.style.background_gradient(
                        subset=["Distance km"], cmap="RdYlGn_r"
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

    # ── Tab 5: White-Space / Gap Analysis ─────────────────────────────────────

    def _tab_whitespace(self, agg: pd.DataFrame, gap_list: list[dict]) -> None:
        """Expansion target cards + combined map (existing + proposed midpoints)."""
        st.subheader("🌍 White-Space Gap Analysis — Expansion Targets")
        st.caption(
            "The largest geographic gaps between existing city nodes represent "
            "the highest-priority unserved markets for new distribution entry."
        )

        if not gap_list:
            st.info("Not enough cities to compute corridor gaps (need ≥ 2 cities).")
            return

        for rank, gap in enumerate(gap_list, start=1):
            urgency = "🔴 High Priority" if rank == 1 else (
                "🟡 Medium Priority" if rank == 2 else "🟢 Watch List"
            )
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**#{rank} — {gap['City A']} → {gap['City B']}**")
                c2.metric("Gap Distance", f"{gap['Gap km']} km")
                c3.metric("Urgency",       urgency)
                st.caption(
                    f"📍 Recommended entry midpoint: "
                    f"Lat {gap['Mid Lat']},  Lon {gap['Mid Lon']}"
                )

        # Build combined map: existing cities + proposed expansion midpoints
        existing_pts = agg[["City", "Latitude", "Longitude", "Total_Sales"]].copy()
        existing_pts["Type"] = "Existing"
        existing_pts["Size"] = existing_pts["Total_Sales"]

        proposal_pts = pd.DataFrame([
            {
                "City":        f"💡 {g['City A'][:5]}–{g['City B'][:5]}",
                "Latitude":    g["Mid Lat"],
                "Longitude":   g["Mid Lon"],
                "Total_Sales": 0,
                "Type":        "Proposed Entry",
                "Size":        50_000,
            }
            for g in gap_list
        ])

        combined = pd.concat([existing_pts, proposal_pts], ignore_index=True)

        fig = px.scatter_mapbox(
            combined,
            lat="Latitude",
            lon="Longitude",
            color="Type",
            color_discrete_map={
                "Existing":       "#00C49F",
                "Proposed Entry": "#B760F3",
            },
            size="Size",
            hover_name="City",
            zoom=5,
            height=500,
            mapbox_style="carto-positron",
            title="Existing Network + Proposed Expansion Midpoints (purple)",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 6: Regional Performance ───────────────────────────────────────────

    def _tab_regional(self, df: pd.DataFrame) -> None:
        """Bar chart + summary dataframe by region."""
        st.subheader("📈 Regional Performance")
        try:
            ragg = (
                df.groupby("Region")
                .agg(Total_Sales=("Sales", "sum"), Txns=("Transactions", "sum"))
                .reset_index()
            )
            ragg["Avg_Value"] = ragg["Total_Sales"] / ragg["Txns"].replace(0, 1)
            ragg = ragg.sort_values("Total_Sales", ascending=False)

            c1, c2 = st.columns([1, 2])
            with c1:
                st.dataframe(
                    ragg.style.format({"Total_Sales": fmt, "Avg_Value": fmt}),
                    hide_index=True,
                    use_container_width=True,
                )
            with c2:
                fig = px.bar(
                    ragg,
                    x="Region",
                    y="Total_Sales",
                    color="Avg_Value",
                    color_continuous_scale=px.colors.sequential.Viridis,
                    title="Sales by Region  (colour = Avg Transaction Value)",
                    template="plotly_white",
                )
                fig.update_layout(yaxis=dict(tickprefix="৳"))
                st.plotly_chart(fig, use_container_width=True)

        except Exception as exc:
            self._error_box(f"Regional performance chart failed: {exc}")

    # ── Tab 7: Product Deep-Dive ───────────────────────────────────────────────

    def _tab_product(self, df: pd.DataFrame) -> None:
        """Region → Product_Category sunburst drill-down."""
        st.subheader("📦 Product Deep-Dive")
        try:
            fig = px.sunburst(
                df,
                path=["Region", "Product_Category"],
                values="Sales",
                color="Sales",
                color_continuous_scale=px.colors.sequential.Blues,
                title="Region → Product Category Revenue Breakdown",
            )
            fig.update_layout(margin=dict(r=10, t=50, l=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            self._error_box(f"Product deep-dive chart failed: {exc}")

    # =========================================================================
    # McKinsey AI Insight Box
    # =========================================================================

    def _render_ai_insights(
        self,
        agg:     pd.DataFrame,
        spatial: dict[str, Any],
    ) -> None:
        """
        Builds a rich, flat context_dict and calls self._insight_box() with a
        prescriptive McKinsey-style what / recommendation pair.

        ── CRITICAL ──────────────────────────────────────────────────────────
        context_data is ALWAYS a flat dict — NEVER a list.
        Sending a list triggers AttributeError: 'list' object has no attribute
        'items' inside BaseModule._build_enriched_context(). Every key here is
        a plain string; every value is a string, int, or float.
        ──────────────────────────────────────────────────────────────────────
        """
        top_city       = agg.loc[agg["Total_Sales"].idxmax()]
        cannibal_pairs = spatial["cannibal_pairs"]
        gap_list       = spatial["gap_list"]

        # ── Grand total KPIs ─────────────────────────────────────────────────
        kpi_block: dict[str, Any] = {
            "Grand Total Sales":        fmt(agg["Total_Sales"].sum()),
            "Grand Total Transactions": int(agg["Total_Txns"].sum()),
            "Total Cities Analysed":    int(len(agg)),
            "Total Regions":            int(agg["Region"].nunique()),
            "Top City":                 str(top_city["City"]),
            "Top City Sales":           fmt(top_city["Total_Sales"]),
            "Top City Transactions":    int(top_city["Total_Txns"]),
        }

        # ── Zone summaries (flat — one entry per zone stat) ───────────────────
        zone_block: dict[str, Any] = {}
        for zone in ["🥇 Golden Zone", "🌱 Emerging Zone", "💀 Dead Zone"]:
            subset = agg[agg["Zone"] == zone]
            if subset.empty:
                continue
            zone_block[f"{zone} — City Count"]     = int(len(subset))
            zone_block[f"{zone} — Combined Sales"] = fmt(subset["Total_Sales"].sum())
            zone_block[f"{zone} — Cities"]         = ", ".join(subset["City"].tolist())

        # ── Cannibalization pairs (flat — one entry per pair) ─────────────────
        cannibal_block: dict[str, Any] = {
            "Cannibalization Risk — Total Pairs": int(len(cannibal_pairs)),
        }
        for idx, pair in enumerate(cannibal_pairs[:5], start=1):
            cannibal_block[f"Risk Pair #{idx}"] = (
                f"{pair['City A']} ↔ {pair['City B']}  ({pair['Distance km']} km)"
            )

        # ── White-space gaps (flat — one entry per gap stat) ──────────────────
        gap_block: dict[str, Any] = {}
        for idx, gap in enumerate(gap_list, start=1):
            gap_block[f"Expansion Target #{idx} — Corridor"] = (
                f"{gap['City A']} → {gap['City B']}"
            )
            gap_block[f"Expansion Target #{idx} — Gap km"]   = float(gap["Gap km"])
            gap_block[f"Expansion Target #{idx} — Midpoint"] = (
                f"({gap['Mid Lat']}, {gap['Mid Lon']})"
            )

        # ── Merge all blocks into one flat dict ───────────────────────────────
        context_dict: dict[str, Any] = {
            **kpi_block,
            **zone_block,
            **cannibal_block,
            **gap_block,
        }

        # ── Derive zone counts for prose statements ───────────────────────────
        golden_count   = int(len(agg[agg["Zone"] == "🥇 Golden Zone"]))
        emerging_count = int(len(agg[agg["Zone"] == "🌱 Emerging Zone"]))
        dead_count     = int(len(agg[agg["Zone"] == "💀 Dead Zone"]))
        risk_count     = len(cannibal_pairs)

        # ── WHAT — quantified situation assessment ────────────────────────────
        what = (
            f"Network of **{len(agg)} cities** across "
            f"{agg['Region'].nunique()} regions generates "
            f"**{fmt(agg['Total_Sales'].sum())}** in total sales. "
            f"K-Means segmentation identifies **{golden_count} Golden Zone**, "
            f"**{emerging_count} Emerging Zone**, and "
            f"**{dead_count} Dead Zone** cities. "
            f"Lead performer is **{top_city['City']}** at "
            f"{fmt(top_city['Total_Sales'])} "
            f"({int(top_city['Total_Txns'])} transactions). "
        ) + (
            f"**{risk_count} cannibalization pair(s)** flagged among Golden Zone nodes. "
            if risk_count > 0 else
            "No cannibalization risk detected within the current threshold. "
        ) + (
            f"Largest unserved corridor: **{gap_list[0]['City A']} → "
            f"{gap_list[0]['City B']}** ({gap_list[0]['Gap km']} km gap)."
            if gap_list else ""
        )

        # ── RECOMMENDATION — three prescriptive directives ────────────────────

        # 1. Cannibalization resolution
        if cannibal_pairs:
            p = cannibal_pairs[0]
            cannibal_action = (
                f"**Resolve cannibalization between {p['City A']} and {p['City B']} "
                f"({p['Distance km']} km apart):** Differentiate these nodes by assigning "
                "distinct SKU portfolios — designate one as a premium flagship and the other "
                "as a high-volume fulfilment hub. This preserves revenue while eliminating "
                "direct self-competition."
            )
        else:
            cannibal_action = (
                "**Maintain geographic discipline:** No cannibalization risk detected. "
                "Enforce a minimum inter-store distance policy of the current threshold "
                "for all future Golden Zone expansion to preserve this competitive separation."
            )

        # 2. White-space entry strategy
        if gap_list:
            g = gap_list[0]
            whitespace_action = (
                f"**Enter the {g['City A']}–{g['City B']} corridor immediately:** "
                f"This {g['Gap km']} km unserved gap represents the highest-priority "
                f"greenfield opportunity. Launch a lean distribution pilot at the "
                f"midpoint ({g['Mid Lat']}, {g['Mid Lon']}) within 90 days. "
                "Use the average Emerging Zone revenue as the conservative breakeven proxy."
            )
        else:
            whitespace_action = (
                "**Deepen market penetration:** No significant unserved corridors detected. "
                "Redirect expansion capex toward growing transaction frequency in "
                "Emerging Zone cities rather than opening new geographic nodes."
            )

        # 3. Dead Zone turnaround / reallocation
        if dead_count > 0:
            dead_action = (
                f"**Execute a 90-day Dead Zone triage on {dead_count} "
                f"underperforming {'city' if dead_count == 1 else 'cities'}:** "
                "Audit SKU relevance, last-mile logistics cost, and local competitor "
                "pricing in each node. Set a hard performance gate: if the unit does not "
                "reach Emerging Zone trajectory by Q2, reallocate its marketing budget "
                "to the highest-growth Emerging Zone cities."
            )
        else:
            dead_action = (
                "**Tighten performance thresholds:** No Dead Zone cities identified. "
                "Raise the K-Means cluster floor to 4 segments to surface "
                "sub-par performers currently masked inside the Emerging Zone cohort."
            )

        recommendation = (
            f"1. {cannibal_action}\n\n"
            f"2. {whitespace_action}\n\n"
            f"3. {dead_action}"
        )

        # ── Call _insight_box — context_data is a flat dict ───────────────────
        self._insight_box(
            what=what,
            recommendation=recommendation,
            context_data=context_dict,   # ← ALWAYS flat dict, never list
        )