"""Placeholder response schemas for non–Sales-Specials offer types.

TODO: production content. These are intentionally small (3-4 fields) and will be
replaced with real per-type schemas later. Each top-level schema exposes a
``records`` list so the shared processor can serialize results generically.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class PromotionItem(_Base):
    """Generic promotion (service specials, schedule service, offer to purchase)."""

    title: str | None = None
    description: str | None = None
    url: str | None = None
    cta: str | None = None


class InventoryItem(_Base):
    """Generic vehicle inventory row (new / certified / used)."""

    title: str | None = None
    vehicle_name: str | None = None
    price: str | None = None
    url: str | None = None


class PromotionResponse(_Base):
    records: list[PromotionItem] = Field(default_factory=list)


class InventoryResponse(_Base):
    records: list[InventoryItem] = Field(default_factory=list)
