"""Unit tests for the offer dedup/normalize logic in the workflow.

These call the static methods directly so we don't construct the full workflow
(which would instantiate the LLM extractor and require an API key).
"""

from app.schemas.llm import OfferExtractionResponse, VehicleIncentiveLLM
from app.workflows.offer_generation_graph import OfferGenerationWorkflow


def _normalize(offers):
    state = {"extraction": OfferExtractionResponse(offers=offers)}
    return OfferGenerationWorkflow._normalize_offers(state)


def test_offer_keys_include_vin_stock_and_vehicle_signature():
    inc = VehicleIncentiveLLM(
        vin_number="ABC123, DEF456",
        stock_number="S1",
        year=2024,
        make="Subaru",
        model="Outback",
    )
    keys = OfferGenerationWorkflow._offer_keys(inc)
    assert ("vin", "abc123") in keys
    assert ("vin", "def456") in keys
    assert ("stock", "s1") in keys
    assert any(k[0] == "vehicle" for k in keys)


def test_duplicate_by_shared_vin_is_collapsed():
    a = VehicleIncentiveLLM(vin_number="VIN1", make="Subaru", model="Outback")
    # Same VIN but different-looking card -> same offer.
    b = VehicleIncentiveLLM(vin_number="VIN1", make="Subaru", model="Outback Premium")
    result = _normalize([a, b])
    assert result["incentive_count"] == 1


def test_vin_less_copy_collapses_onto_vehicle_signature():
    a = VehicleIncentiveLLM(
        year=2024, make="Subaru", model="Outback", lowest_monthly_payment=329
    )
    b = VehicleIncentiveLLM(
        year=2024,
        make="Subaru",
        model="Outback",
        lowest_monthly_payment=329,
        vin_number="VIN9",
    )
    result = _normalize([a, b])
    assert result["incentive_count"] == 1


def test_distinct_offers_are_kept_and_renumbered():
    a = VehicleIncentiveLLM(year=2024, make="Subaru", model="Outback", stock_number="S1")
    b = VehicleIncentiveLLM(year=2024, make="Subaru", model="Forester", stock_number="S2")
    result = _normalize([a, b])
    assert result["incentive_count"] == 2
    priorities = [i.offer_priority for i in result["incentives"]]
    assert priorities == ["Vehicle #1", "Vehicle #2"]


def test_offer_emphasis_reset_to_none_after_normalize():
    a = VehicleIncentiveLLM(stock_number="S1", offer_emphasis="Starburst")
    result = _normalize([a])
    assert result["incentives"][0].offer_emphasis is None
