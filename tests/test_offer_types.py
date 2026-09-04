from app.config.offer_types import (
    DEFAULT_OFFER_TYPE,
    OfferType,
    normalize_offer_type,
    supported_values,
)
from app.core.exceptions import UnsupportedOfferTypeError
import pytest


def test_default_is_sales_specials():
    assert DEFAULT_OFFER_TYPE == OfferType.SALES_SPECIALS
    assert normalize_offer_type(None) == OfferType.SALES_SPECIALS
    assert normalize_offer_type("") == OfferType.SALES_SPECIALS


def test_normalize_accepts_internal_and_labels():
    assert normalize_offer_type("sales_specials") == OfferType.SALES_SPECIALS
    assert normalize_offer_type("Sales Specials") == OfferType.SALES_SPECIALS
    assert normalize_offer_type("service specials") == OfferType.SERVICE_SPECIALS
    assert normalize_offer_type("Used Inventory") == OfferType.USED_INVENTORY
    assert normalize_offer_type(OfferType.NEW_INVENTORY) == OfferType.NEW_INVENTORY


def test_supported_values():
    assert supported_values() == [
        "sales_specials",
        "service_specials",
        "schedule_service",
        "new_inventory",
        "certified_inventory",
        "used_inventory",
        "offer_to_purchase",
    ]


def test_invalid_type_raises_with_allowed_list():
    with pytest.raises(UnsupportedOfferTypeError) as exc:
        normalize_offer_type("homepage")
    message = str(exc.value)
    assert "homepage" in message
    assert "sales_specials" in message
    assert "offer_to_purchase" in message
