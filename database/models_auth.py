"""
database/models_auth.py  ·  FinOx Suite
=========================================
ORM model for the User table.

Columns
-------
id            : int (PK, auto)
email         : str (unique, indexed)
password_hash : str (bcrypt hash — never store plaintext)
user_code     : str (unique access code, e.g. FNOX-8A9B-C7D6)
display_name  : str
created_at    : datetime
last_login    : datetime (nullable)
is_active     : bool
"""
from __future__ import annotations

import hashlib
import os
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class User(Base):
    __tablename__ = "users"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Identity ─────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Repr ─────────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} code={self.user_code!r}>"

    # =========================================================================
    # Class-level helpers
    # =========================================================================

    @staticmethod
    def generate_user_code() -> str:
        """
        Generate a unique human-readable access code.
        Format: FNOX-XXXX-XXXX  (hex digits, uppercase)
        Example: FNOX-8A9B-C7D6
        """
        chars = string.ascii_uppercase + string.digits
        part1 = "".join(secrets.choice(chars) for _ in range(4))
        part2 = "".join(secrets.choice(chars) for _ in range(4))
        return f"FNOX-{part1}-{part2}"

    @staticmethod
    def hash_password(plaintext: str) -> str:
        """
        SHA-256 + per-user salt.
        For production, swap for bcrypt:
            import bcrypt; bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        """
        salt = secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}{plaintext}".encode("utf-8")).hexdigest()
        return f"{salt}${digest}"

    def verify_password(self, plaintext: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        try:
            salt, digest = self.password_hash.split("$", 1)
            expected = hashlib.sha256(f"{salt}{plaintext}".encode("utf-8")).hexdigest()
            return secrets.compare_digest(expected, digest)
        except Exception:
            return False
