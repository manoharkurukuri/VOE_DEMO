from fastapi import APIRouter, Query

from app.core.config import settings
from app.events.broker import scrape_broker

router = APIRouter(prefix=f"{settings.api_v1_prefix}/offers", tags=["offers"])


@router.get("/generate")
def generate_offers(
    excel_path: str = Query(
        default="offers/MWK00012GMC_Dealership_URLs.xlsx",
        description="Path to the dealer-URL Excel workbook to process.",
    ),
) -> dict[str, str]:
    """Publish an offer-generation event and return immediately.

    Stage B (scrape) picks up the event, scrapes each dealer's Sales Specials URLs
    in parallel, and fans out per-dealer data to stage C (extract), which runs the
    LLM and writes each dealer's Excel zip in the storage/offers folder.
    """
    scrape_broker.publish({"excel_path": excel_path})
    return {
        "status": "processing",
        "message": "Your request has been accepted and is being processed. "
        "Offers will be generated in a few minutes.",
        "excel_path": excel_path,
    }
