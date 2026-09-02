from typing import Any

import logfire

from app.events.broker import extract_broker
from app.service.offer_generation_service import OfferGenerationService

# Reuse one service (LLM client pool + compiled graph) across events.
_service: OfferGenerationService | None = None


def _get_service() -> OfferGenerationService:
    global _service
    if _service is None:
        _service = OfferGenerationService()
    return _service


def handle_scrape_event(event: dict[str, Any]) -> None:
    """Stage B subscriber: scrape every dealer's Sales Specials URLs and publish
    each dealer to the extract broker (stage C) as soon as that dealer's URLs
    finish scraping, so extraction overlaps with the remaining scraping."""
    excel_path = event["excel_path"]
    logfire.info("Scraping dealer URLs", excel_path=excel_path)

    source_file, payloads = _get_service().scrape_dealers(
        excel_path, on_dealer_ready=extract_broker.publish
    )

    logfire.info(
        "Scraping stage completed; all dealers dispatched to extract",
        source_file=source_file,
        dealer_count=len(payloads),
    )


def handle_extract_event(event: dict[str, Any]) -> None:
    """Stage C subscriber: extract offers for one dealer (LLM sequential per dealer)
    and write the dealer's Excel zip + error file."""
    dealer_id = event.get("dealer_id")
    logfire.info("Extracting offers for dealer", dealer_id=dealer_id)

    result = _get_service().build_dealer(event)

    logfire.info(
        "Dealer extraction completed",
        dealer_id=result.dealer_id,
        zip_name=result.zip_name,
        error_file_name=result.error_file_name,
    )

