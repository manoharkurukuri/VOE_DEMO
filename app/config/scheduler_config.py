"""Centralized per-type scheduler configuration.

Maps each offer type to its cron expression (sourced from settings so it can be
overridden per environment). Each type runs once a month on the 5th, staggered
to a different hour by default:

    sales_specials       -> 5th @ 01:00
    service_specials     -> 5th @ 02:00
    schedule_service     -> 5th @ 03:00
    new_inventory        -> 5th @ 04:00
    certified_inventory  -> 5th @ 05:00
    used_inventory       -> 5th @ 06:00
    offer_to_purchase    -> 5th @ 07:00
"""

from __future__ import annotations

from app.config.offer_types import OfferType
from app.core.config import settings


def schedule_config() -> dict[OfferType, str]:
    """Return the cron expression for every offer type (env-overridable)."""
    return {
        OfferType.SALES_SPECIALS: settings.schedule_sales_specials,
        OfferType.SERVICE_SPECIALS: settings.schedule_service_specials,
        OfferType.SCHEDULE_SERVICE: settings.schedule_schedule_service,
        OfferType.NEW_INVENTORY: settings.schedule_new_inventory,
        OfferType.CERTIFIED_INVENTORY: settings.schedule_certified_inventory,
        OfferType.USED_INVENTORY: settings.schedule_used_inventory,
        OfferType.OFFER_TO_PURCHASE: settings.schedule_offer_to_purchase,
    }
