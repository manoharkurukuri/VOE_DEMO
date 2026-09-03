"""Tests for OfferGenerationService (app.service.offer_generation_service).

Assembly/zip/error-file logic is unit-tested with a bare service instance (built
without __init__ so no API key is needed). The full scrape+extract+zip pipeline
is an ``integration`` test that hits the live page and Gemini.
"""

import zipfile

import pytest

from app.core.exceptions import FileStorageError
from app.schemas.offer import GenerateOffersResult
from app.service.offer_generation_service import OfferGenerationService, _UrlResult
from tests.conftest import requires_gemini_key


@pytest.fixture
def bare_service(tmp_path):
    """A service instance without __init__, so no LLM key/browser is required."""
    svc = object.__new__(OfferGenerationService)
    svc.timezone_name = "Asia/Kolkata"
    svc.storage_dir = tmp_path
    return svc


def test_assemble_dealer_writes_zip_and_error_file(bare_service):
    results = [
        _UrlResult(
            order=0,
            dealer_id="D1",
            dealer_name="Flow Subaru",
            oem="Subaru",
            url="https://example.com/a",
            count=2,
            file_name="a.xlsx",
            file_bytes=b"PK-fake-xlsx",
        ),
        _UrlResult(
            order=1,
            dealer_id="D1",
            dealer_name="Flow Subaru",
            oem="Toyota",
            url="https://example.com/b",
            count=0,
            error_message="URL: https://example.com/b\nOEM: Toyota\nError: No offers were extracted from this page.",
        ),
    ]
    result = bare_service._assemble_dealer("D1", "Flow Subaru", results, "20240101")

    assert result.dealer_id == "D1"
    assert result.offer_counts == {"Subaru": 2, "Toyota": 0}
    assert result.zip_name and result.zip_path
    assert result.error_file_name and result.error_file_path
    assert result.errors["Toyota"] == "No offers were extracted from this page."

    # The zip on disk actually contains the workbook.
    with zipfile.ZipFile(result.zip_path) as zf:
        assert zf.namelist() == ["a.xlsx"]
        assert zf.read("a.xlsx") == b"PK-fake-xlsx"

    # The error text file was written.
    with open(result.error_file_path, encoding="utf-8") as fh:
        assert "Toyota" in fh.read()


def test_assemble_dealer_no_offers_produces_no_zip(bare_service):
    results = [
        _UrlResult(
            order=0,
            dealer_id="D2",
            dealer_name="Empty",
            oem="Subaru",
            url="https://example.com/x",
            count=0,
            error_message="URL: x\nOEM: Subaru\nError: boom",
        )
    ]
    result = bare_service._assemble_dealer("D2", "Empty", results, "20240101")
    assert result.zip_name is None
    assert result.error_file_name is not None


def test_write_zip_and_text_roundtrip(bare_service):
    zip_name, zip_path = bare_service._write_zip("out.zip", [("f.xlsx", b"data")])
    assert zip_name == "out.zip"
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.read("f.xlsx") == b"data"

    name, path = bare_service._write_text("note.txt", "hello")
    assert name == "note.txt"
    with open(path, encoding="utf-8") as fh:
        assert fh.read() == "hello"


def test_scrape_dealers_missing_columns_raises(bare_service, tmp_path):
    import pandas as pd

    bad = tmp_path / "bad.xlsx"
    pd.DataFrame([{"id": "1", "url": "u"}]).to_excel(bad, index=False)
    with pytest.raises(FileStorageError):
        bare_service.scrape_dealers(bad)


@pytest.mark.integration
@requires_gemini_key
def test_live_generate_from_excel(dealer_workbook, tmp_path, monkeypatch):
    """Full pipeline against the live dealer page + Gemini."""
    import app.service.offer_generation_service as mod

    # Redirect output to a temp storage dir so nothing lands in ./storage.
    monkeypatch.setattr(mod.settings, "local_storage_dir", str(tmp_path / "out"))

    service = OfferGenerationService()
    result = service.generate_from_excel(dealer_workbook)

    assert isinstance(result, GenerateOffersResult)
    assert len(result.dealers) == 1
    dealer = result.dealers[0]
    assert dealer.dealer_id == "TEST001"
    # Either offers were found (zip) or a diagnostic error file was written.
    assert dealer.zip_path or dealer.error_file_path
