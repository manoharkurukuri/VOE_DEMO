"""Unit tests for the LLM schema + validators (app.schemas.llm)."""

from app.schemas.llm import (
    OfferExtractionResponse,
    OfferType,
    PaymentType,
    VehicleIncentiveLLM,
    VehicleType,
)


def test_currency_strings_are_parsed_to_floats():
    inc = VehicleIncentiveLLM(msrp="$32,500.00", lowest_monthly_payment="$329")
    assert inc.msrp == 32500.0
    assert inc.lowest_monthly_payment == 329.0


def test_null_like_strings_become_none():
    inc = VehicleIncentiveLLM(make="N/A", model="unknown", trim="-", stock_number="")
    assert inc.make is None
    assert inc.model is None
    assert inc.trim is None
    assert inc.stock_number is None


def test_integer_fields_parsed_from_text():
    inc = VehicleIncentiveLLM(year="2024", annual_mileage="10,000 miles")
    assert inc.year == 2024
    assert inc.annual_mileage == 10000


def test_out_of_range_values_are_rejected():
    inc = VehicleIncentiveLLM(
        year=1800,  # below 1980
        lease_term_months=200,  # above 120
        annual_mileage=0,  # not > 0
        finance_rate=250,  # above 100
    )
    assert inc.year is None
    assert inc.lease_term_months is None
    assert inc.annual_mileage is None
    assert inc.finance_rate is None


def test_enum_aliases_are_normalized():
    inc = VehicleIncentiveLLM(
        offer_type="financing offer",
        vehicle_type="certified pre-owned",
        down_payment_or_due_at_signing="due at lease signing",
    )
    # use_enum_values=True stores the raw enum value strings.
    assert inc.offer_type == OfferType.FINANCE.value
    assert inc.vehicle_type == VehicleType.CPO.value
    assert inc.down_payment_or_due_at_signing == PaymentType.DUE_AT_SIGNING.value


def test_unknown_enum_becomes_none():
    inc = VehicleIncentiveLLM(offer_type="mystery offer", vehicle_type="spaceship")
    assert inc.offer_type is None
    assert inc.vehicle_type is None


def test_offer_emphasis_is_forced_null():
    inc = VehicleIncentiveLLM(offer_emphasis="Starburst!")
    assert inc.offer_emphasis is None


def test_finance_rate_percent_is_preserved_as_number():
    inc = VehicleIncentiveLLM(finance_rate="1.9%")
    assert inc.finance_rate == 1.9


def test_extraction_response_defaults_to_empty_list():
    resp = OfferExtractionResponse()
    assert resp.offers == []


def test_extraction_response_ignores_extra_fields():
    resp = OfferExtractionResponse(offers=[{"make": "Subaru"}], junk="ignored")
    assert len(resp.offers) == 1
    assert resp.offers[0].make == "Subaru"
