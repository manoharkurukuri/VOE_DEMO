"""certified_inventory processor (placeholder).

Reuses the shared scrape + LLM flow from :class:`BaseProcessor`. Emits simple
JSON output for now. TODO: production extraction/serialization.
"""

from __future__ import annotations

from app.config.offer_types import OfferType
from app.processors.base import BaseProcessor
from app.prompts.certified_inventory import SYSTEM_PROMPT
from app.response_templates.certified_inventory import RESPONSE_SCHEMA


class CertifiedInventoryProcessor(BaseProcessor):
    offer_type = OfferType.CERTIFIED_INVENTORY
    prompt = SYSTEM_PROMPT
    response_schema = RESPONSE_SCHEMA
