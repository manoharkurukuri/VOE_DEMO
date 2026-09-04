"""schedule_service processor (placeholder).

Reuses the shared scrape + LLM flow from :class:`BaseProcessor`. Emits simple
JSON output for now. TODO: production extraction/serialization.
"""

from __future__ import annotations

from app.config.offer_types import OfferType
from app.processors.base import BaseProcessor
from app.prompts.schedule_service import SYSTEM_PROMPT
from app.response_templates.schedule_service import RESPONSE_SCHEMA


class ScheduleServiceProcessor(BaseProcessor):
    offer_type = OfferType.SCHEDULE_SERVICE
    prompt = SYSTEM_PROMPT
    response_schema = RESPONSE_SCHEMA
