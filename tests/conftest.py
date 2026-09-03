"""Shared pytest fixtures and helpers for the Vehicle Offer Extraction suite.

The unit tests here exercise in-process modules (broker, excel, schemas, dedup)
with no network or API key. The tests marked ``integration`` hit real services
(a live dealer page via Playwright and the Gemini LLM) and are skipped when the
required credentials/tools are unavailable.
"""

import pandas as pd
import pytest
from dotenv import load_dotenv

# Load .env so GEMINI_API_KEY (and friends) are available to integration tests.
load_dotenv()

# Live dealer "Sales Specials" page used by the integration tests.
TEST_URL = "https://www.flowsubaruwinstonsalem.com/promotions/new/index.htm"

# A small chunk of offer-like text fed to the LLM in the extractor integration
# test, so it does not depend on the scraper succeeding first.
SAMPLE_OFFER_TEXT = """
2024 Subaru Outback Premium
Lease for $329/month for 36 months.
$3,499 due at signing. 10,000 miles per year.
Stock #S12345. VIN: 4S4BTANC1P1234567. MSRP $32,500.
Disclaimer: Closed-end lease available on a 2024 Subaru Outback Premium.
Vehicle shown for illustration purposes only.

2024 Subaru Forester
1.9% APR financing for 48 months on approved credit.
Stock #F98765.
""".strip()


def gemini_key_available() -> bool:
    """True when at least one Gemini API key is configured."""
    from app.core.config import settings

    return bool(settings.resolved_api_keys())


# Reusable skip marker for tests that need a real Gemini key.
requires_gemini_key = pytest.mark.skipif(
    not gemini_key_available(),
    reason="No GEMINI_API_KEY configured; skipping live LLM test.",
)


@pytest.fixture
def sample_incentive():
    """A fully-populated VehicleIncentiveLLM for excel/dedup tests."""
    from app.schemas.llm import VehicleIncentiveLLM

    return VehicleIncentiveLLM(
        offer_type="Lease Offer",
        vehicle_type="New",
        year=2024,
        make="Subaru",
        model="Outback",
        trim="Premium",
        stock_number="S12345",
        vin_number="4S4BTANC1P1234567",
        msrp=32500,
        lowest_monthly_payment=329,
        lease_term_months=36,
        down_payment_or_due_at_signing="Due at Signing",
        total_due_at_signing=3499,
        annual_mileage=10000,
        finance_rate=1.9,
        finance_term_months=48,
        disclaimer="Closed-end lease available on a 2024 Subaru Outback Premium.",
    )


@pytest.fixture
def dealer_workbook(tmp_path):
    """Create a temporary dealer-URL workbook pointing at the live test URL.

    Returns the path to an .xlsx with the columns the service requires plus one
    ``Sales Specials`` row for the live dealer page.
    """
    path = tmp_path / "dealers.xlsx"
    df = pd.DataFrame(
        [
            {
                "id": "TEST001",
                "DealerName": "Flow Subaru Winston Salem",
                "oem": "Subaru",
                "type": "Sales Specials",
                "url": TEST_URL,
            },
            {
                "id": "TEST001",
                "DealerName": "Flow Subaru Winston Salem",
                "oem": "Subaru",
                "type": "Service Specials",
                "url": "https://example.com/service",
            },
        ]
    )
    df.to_excel(path, index=False)
    return path
