"""Tests for the LLM offer extractor (app.service.llm_extractor).

The live extraction runs against the real Gemini API and needs a key; it is
marked ``integration`` and skipped when no key is configured.
"""

import pytest

from app.core.exceptions import LLMExtractionError
from app.schemas.llm import OfferExtractionResponse
from tests.conftest import SAMPLE_OFFER_TEXT, requires_gemini_key


def test_missing_api_key_raises(monkeypatch):
    import app.service.llm_extractor as mod

    monkeypatch.setattr(type(mod.settings), "resolved_api_keys", lambda self: [])
    with pytest.raises(LLMExtractionError):
        mod.LLMOfferExtractor()


@pytest.mark.integration
@requires_gemini_key
def test_live_extract_returns_structured_offers():
    from app.service.llm_extractor import LLMOfferExtractor

    extractor = LLMOfferExtractor()
    result = extractor.extract(SAMPLE_OFFER_TEXT)

    assert isinstance(result, OfferExtractionResponse)
    assert isinstance(result.offers, list)
    # The sample text clearly describes at least one sales offer.
    assert len(result.offers) >= 1
    makes = {(o.make or "").lower() for o in result.offers}
    assert any("subaru" in m for m in makes)
