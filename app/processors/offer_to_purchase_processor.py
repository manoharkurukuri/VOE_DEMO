"""offer_to_purchase processor (placeholder).

Reuses the shared scrape + LLM flow from :class:`BaseProcessor`. Emits simple
JSON output for now. TODO: production extraction/serialization.
"""

from __future__ import annotations

from app.config.offer_types import OfferType
from app.processors.base import BaseProcessor
from app.prompts.offer_to_purchase import SYSTEM_PROMPT
from app.response_templates.offer_to_purchase import RESPONSE_SCHEMA


class OfferToPurchaseProcessor(BaseProcessor):
    offer_type = OfferType.OFFER_TO_PURCHASE
    prompt = SYSTEM_PROMPT
    response_schema = RESPONSE_SCHEMA
