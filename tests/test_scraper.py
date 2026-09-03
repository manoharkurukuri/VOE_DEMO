"""Tests for the scraper (app.service.scraper).

The pure helpers are unit-tested; the full browser fetch against the live dealer
page is marked ``integration``.
"""

import pytest

from app.service import scraper
from app.service.scraper import ScrapingError, _is_challenge, get_website_content_from_url
from tests.conftest import TEST_URL


def test_is_challenge_detects_block_markers():
    assert _is_challenge("<html>Just a moment...</html>")
    assert _is_challenge("Checking your browser before accessing")
    assert not _is_challenge("<html><body>2024 Subaru Outback $329/mo</body></html>")


def test_get_website_content_parses_title_and_body(monkeypatch):
    html = """
    <html>
      <head><title>Specials</title></head>
      <body>
        <header>Nav Menu</header>
        <main>2024 Subaru Outback lease $329/mo</main>
        <footer>Footer legal</footer>
      </body>
    </html>
    """
    monkeypatch.setattr(scraper, "fetch_html", lambda url: html)
    result = get_website_content_from_url("https://example.com")
    assert result["title"] == "Specials"
    assert "Subaru Outback" in result["body"]
    assert result["header"] == "Nav Menu"
    assert result["footer"] == "Footer legal"
    # Header/footer/nav are stripped from the body.
    assert "Nav Menu" not in result["body"]


def test_empty_body_raises_scraping_error(monkeypatch):
    monkeypatch.setattr(
        scraper, "fetch_html", lambda url: "<html><body></body></html>"
    )
    with pytest.raises(ScrapingError):
        get_website_content_from_url("https://example.com")


def test_fetch_failure_wrapped_as_scraping_error(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(scraper, "fetch_html", boom)
    with pytest.raises(ScrapingError):
        get_website_content_from_url("https://example.com")


@pytest.mark.integration
def test_live_scrape_returns_body():
    """Hit the real dealer page with Playwright and confirm we get content back."""
    result = get_website_content_from_url(TEST_URL)
    assert result["url"] == TEST_URL
    assert isinstance(result["body"], str)
    assert len(result["body"]) > 100
