"""Per-offer-type output directory helpers.

All generated files are separated by offer type so ZIPs and error files never mix
between types:

    <local_storage_dir>/<offer_type>/zip/
    <local_storage_dir>/<offer_type>/errors/

Use these helpers instead of constructing paths by hand.
"""

from __future__ import annotations

from pathlib import Path

from app.config.offer_types import OfferType, normalize_offer_type
from app.core.config import settings


def _root() -> Path:
    return Path(settings.local_storage_dir)


def get_output_directory(offer_type: str | OfferType) -> Path:
    """Base output directory for a type, e.g. ``storage/offers/sales_specials``."""
    resolved = normalize_offer_type(offer_type)
    path = _root() / resolved.value
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_zip_directory(offer_type: str | OfferType) -> Path:
    """ZIP output directory for a type, e.g. ``.../sales_specials/zip``."""
    path = get_output_directory(offer_type) / "zip"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_error_directory(offer_type: str | OfferType) -> Path:
    """Error output directory for a type, e.g. ``.../sales_specials/errors``."""
    path = get_output_directory(offer_type) / "errors"
    path.mkdir(parents=True, exist_ok=True)
    return path
