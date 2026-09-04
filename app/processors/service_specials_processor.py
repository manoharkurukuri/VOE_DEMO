"""service_specials processor (placeholder).

Reuses the shared scrape + LLM flow from :class:`BaseProcessor`. Emits simple
JSON output for now. TODO: production extraction/serialization.
"""

from __future__ import annotations

from app.config.offer_types import OfferType
from app.processors.base import BaseProcessor
from app.prompts.service_specials import SYSTEM_PROMPT
from app.response_templates.service_specials import RESPONSE_SCHEMA


class ServiceSpecialsProcessor(BaseProcessor):
    offer_type = OfferType.SERVICE_SPECIALS
    prompt = SYSTEM_PROMPT
    response_schema = RESPONSE_SCHEMA
