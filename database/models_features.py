"""
database/models_features.py  ·  FinOx Suite
=============================================
ORM models for feature-specific persisted data.
All rows carry a user_code FK for strict data isolation.

Models
------
UserApiKey         — encrypted API keys per provider per user
UserDashboardState — saved sidebar/financial params per user
SavedInventoryParam— saved EOQ/reorder-point params per user
HRCsvState         — column mapping state saved per user
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


# ---------------------------------------------------------------------------
# Helper timestamp default
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# UserApiKey
# ---------------------------------------------------------------------------
class UserApiKey(Base):
    """
    Stores one API key per (user_code, provider) pair.
    Key is stored as-is (session-encrypted at the application layer).
    For true production use, encrypt with Fernet before storing.
    """
    __tablename__ = "user_api_keys"

    id: Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_code: Mapped[str]    = mapped_column(String(20), nullable=False, index=True)
    provider: Mapped[str]     = mapped_column(String(30), nullable=False)   # openai|gemini|grok
    api_key_enc: Mapped[str]  = mapped_column(Text, nullable=False)         # store masked/enc
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return f"<UserApiKey user={self.user_code!r} provider={self.provider!r}>"


# ---------------------------------------------------------------------------
# UserDashboardState
# ---------------------------------------------------------------------------
class UserDashboardState(Base):
    """
    Persists the sidebar financial parameters so users don't need to
    re-enter them on every session.
    """
    __tablename__ = "user_dashboard_states"

    id: Mapped[int]              = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_code: Mapped[str]       = mapped_column(String(20), nullable=False, unique=True, index=True)

    price: Mapped[float]         = mapped_column(Float, nullable=False, default=500.0)
    qty: Mapped[float]           = mapped_column(Float, nullable=False, default=1000.0)
    var_cost: Mapped[float]      = mapped_column(Float, nullable=False, default=200.0)
    fixed_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=150_000.0)
    capex_init: Mapped[float]    = mapped_column(Float, nullable=False, default=2_500_000.0)
    forecast_years: Mapped[int]  = mapped_column(Integer, nullable=False, default=5)
    dep_years: Mapped[int]       = mapped_column(Integer, nullable=False, default=7)
    tax_rate: Mapped[float]      = mapped_column(Float, nullable=False, default=0.25)
    rev_growth: Mapped[float]    = mapped_column(Float, nullable=False, default=0.10)
    vc_inflation: Mapped[float]  = mapped_column(Float, nullable=False, default=0.03)
    fc_inflation: Mapped[float]  = mapped_column(Float, nullable=False, default=0.05)
    discount_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.12)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def to_params_dict(self) -> dict:
        """Convert this row to the params dict consumed by modules."""
        return {
            "price":          self.price,
            "qty":            self.qty,
            "var_cost":       self.var_cost,
            "fixed_monthly":  self.fixed_monthly,
            "capex_init":     self.capex_init,
            "forecast_years": self.forecast_years,
            "dep_years":      self.dep_years,
            "tax_rate":       self.tax_rate,
            "rev_growth":     self.rev_growth,
            "vc_inflation":   self.vc_inflation,
            "fc_inflation":   self.fc_inflation,
            "discount_rate":  self.discount_rate,
        }

    def __repr__(self) -> str:
        return f"<DashboardState user={self.user_code!r}>"


# ---------------------------------------------------------------------------
# SavedInventoryParam
# ---------------------------------------------------------------------------
class SavedInventoryParam(Base):
    """
    Persists EOQ / reorder-point parameters per user so they survive
    page navigations.
    """
    __tablename__ = "saved_inventory_params"

    id: Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_code: Mapped[str]     = mapped_column(String(20), nullable=False, unique=True, index=True)

    annual_demand: Mapped[float]  = mapped_column(Float, nullable=False, default=12_000.0)
    order_cost: Mapped[float]     = mapped_column(Float, nullable=False, default=500.0)
    holding_cost: Mapped[float]   = mapped_column(Float, nullable=False, default=50.0)
    lead_time_days: Mapped[int]   = mapped_column(Integer, nullable=False, default=14)
    safety_stock: Mapped[float]   = mapped_column(Float, nullable=False, default=200.0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return f"<InventoryParam user={self.user_code!r}>"


# ---------------------------------------------------------------------------
# HRCsvState
# ---------------------------------------------------------------------------
class HRCsvState(Base):
    """
    Remembers which column the user mapped to which HR field,
    so large files don't need to be re-uploaded / re-mapped each session.
    Stored as a JSON string in `column_map_json`.
    """
    __tablename__ = "hr_csv_states"

    id: Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_code: Mapped[str]          = mapped_column(String(20), nullable=False, unique=True, index=True)
    original_filename: Mapped[str]  = mapped_column(String(255), nullable=False, default="")
    column_map_json: Mapped[str]    = mapped_column(Text, nullable=False, default="{}")
    row_count: Mapped[int]          = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return f"<HRCsvState user={self.user_code!r} file={self.original_filename!r}>"
