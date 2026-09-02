"""Playwright + BeautifulSoup scraping logic, packaged to run inside AWS Lambda.

This is a self-contained copy of the scraping code that used to live in the
backend (``app/services/scraper.py``). It has no dependency on the FastAPI app so
it can be built into a small, single-purpose Lambda container image.
"""

import os
import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class ScrapingError(Exception):
    """Raised when the page cannot be scraped (bot wall, empty body, etc.)."""



_BLOCK_MARKERS = (
    "working to keep your website experience safe",
    "attention required",
    "just a moment",
    "checking your browser",
    "enable javascript and cookies",
    "__cf_chl",
    "challenge-platform",
    "cf-chl",
)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# Chromium flags required to run headless Chromium inside the Lambda sandbox,
# where there is no GPU, limited /dev/shm, and only /tmp is writable.
# --single-process/--no-zygote crash desktop Chromium, so they are Lambda-only.
_LAMBDA_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--single-process",
    "--no-zygote",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
]

# Safe flags for running headless Chromium on a normal desktop/server.
_DESKTOP_CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
]


def _chromium_args() -> list[str]:
    """Use the aggressive Lambda flags only inside Lambda; they crash locally."""
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return _LAMBDA_CHROMIUM_ARGS
    return _DESKTOP_CHROMIUM_ARGS


def _headless() -> bool:
    """Headless by default; set SCRAPER_HEADLESS=false to watch the browser."""
    return os.getenv("SCRAPER_HEADLESS", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }



def _is_challenge(html: str) -> bool:
    lowered = html.lower()
    return any(marker in lowered for marker in _BLOCK_MARKERS)


# Buttons/links that hide the real offer terms behind a modal or accordion.
_DETAIL_TRIGGER_RE = re.compile(
    r"(see\s+(offer\s+)?details|view\s+(disclaimer|details|offer|terms)"
    r"|disclaimer|details|terms|full\s+offer|offer\s+details|show\s+more)",
    re.I,
)


def _expand_and_collect_details(page) -> None:
    """Click detail/disclaimer buttons + accordions so hidden offer terms
    (pricing, disclaimers, due-at-signing, etc.) are revealed into the DOM."""
    collected: list[str] = []

    # 1. Modal-opening buttons (safe: no page navigation).
    try:
        triggers = page.get_by_role("button", name=_DETAIL_TRIGGER_RE)
        count = min(triggers.count(), 25)
    except Exception:
        count = 0

    for i in range(count):
        try:
            trigger = triggers.nth(i)
            trigger.scroll_into_view_if_needed(timeout=2000)
            trigger.click(timeout=2500)
            page.wait_for_timeout(500)
            dialog = page.locator(
                "[role='dialog']:visible, [aria-modal='true']:visible, "
                ".modal:visible, [class*='modal']:visible, [class*='dialog']:visible"
            )
            if dialog.count():
                text = dialog.first.inner_text(timeout=2000)
                if text and text.strip():
                    collected.append(text.strip())
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
        except Exception:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            continue

    # 2. Collapsed accordions/expanders (in-page, no navigation).
    try:
        toggles = page.locator("[aria-expanded='false']")
        for i in range(min(toggles.count(), 30)):
            try:
                toggles.nth(i).click(timeout=1200)
                page.wait_for_timeout(150)
            except Exception:
                continue
    except Exception:
        pass

    # Inject collected modal text so it survives page.content() extraction.
    if collected:
        joined = "\n\n".join(dict.fromkeys(collected))
        try:
            page.evaluate(
                "(t) => { const d = document.createElement('div');"
                " d.setAttribute('data-scraped-details','1');"
                " d.style.display='none'; d.innerText = t;"
                " document.body.appendChild(d); }",
                joined,
            )
        except Exception:
            pass


def _collect_iframe_text(page) -> None:
    """Some dealer specials render inside an <iframe> (third-party incentive
    widgets). ``page.content()`` only returns the top frame, so the offers never
    reach the extracted body. Pull each child frame's visible text into the main
    DOM so it survives ``page.content()`` extraction."""
    collected: list[str] = []
    for frame in page.frames:
        if frame is page.main_frame:
            continue
        try:
            text = frame.evaluate(
                "() => (document.body ? document.body.innerText : '')"
            )
        except Exception:
            continue
        if text and text.strip():
            collected.append(text.strip())

    if not collected:
        return

    joined = "\n\n".join(dict.fromkeys(collected))
    try:
        page.evaluate(
            "(t) => { const d = document.createElement('div');"
            " d.setAttribute('data-scraped-iframe','1');"
            " d.style.display='none'; d.innerText = t;"
            " document.body.appendChild(d); }",
            joined,
        )
    except Exception:
        pass


# Truthy when the page shows real vehicle/offer content (cards or pricing terms)
# rather than a loading spinner or a "no results" placeholder.
_OFFER_READY_JS = r"""
() => {
    const text = document.body ? document.body.innerText : '';
    const hasPricing = /\$\s?\d[\d,]{2,}/.test(text)
        || /per\s*month|\/mo\b|\bMSRP\b|\bAPR\b|due at signing|lease/i.test(text);
    const cards = document.querySelectorAll(
        "[class*='vehicle-card'], [data-vehicle], [class*='vehicleCard'], "
        + "[class*='special'], [class*='offer'], [class*='incentive'], "
        + "[itemtype*='Vehicle'], [class*='inventory'] article"
    ).length;
    return hasPricing || cards > 2;
}
"""

# Times to reload a page whose flaky inventory AJAX returned the empty "no
# results" placeholder, retrying until the real offer cards render.
_MAX_OFFER_RELOADS = 3


def _wait_for_offer_content(page, timeout_ms: int = 25000) -> None:
    """Wait until the real offer/vehicle content renders (AJAX inventory widgets),
    so extraction doesn't run against an empty placeholder. Best-effort: returns
    quietly if nothing matches within the timeout."""
    try:
        page.wait_for_function(_OFFER_READY_JS, timeout=timeout_ms)
    except Exception:
        pass


def _offers_present(page) -> bool:
    """True when offer/vehicle content is currently in the DOM."""
    try:
        return bool(page.evaluate(_OFFER_READY_JS))
    except Exception:
        return False


def _load_dynamic_content(page) -> None:
    """Give JS-rendered offer widgets time to load and trigger lazy content."""
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    # Many dealer specials pages (e.g. DealerInspire) ship a "no results"
    # placeholder and swap in the vehicle/offer cards a few seconds later via an
    # AJAX call. Wait for that real offer content to appear instead of guessing
    # with a fixed sleep, so we don't extract the empty placeholder.
    _wait_for_offer_content(page, timeout_ms=25000)

    # The inventory AJAX (e.g. DealerInspire's Algolia-powered results) is flaky
    # and often returns the empty "no results" placeholder on some loads. Reload
    # and wait again, up to a few times, until the real offer cards appear. Clear
    # cookies each retry so the site treats it as a fresh visitor, which can get
    # past a session that got stuck on "no results".
    reloads = 0
    while not _offers_present(page) and reloads < _MAX_OFFER_RELOADS:
        reloads += 1
        try:
            page.context.clear_cookies()
        except Exception:
            pass
        try:
            page.reload(wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        _wait_for_offer_content(page, timeout_ms=25000)

    # Many dealer specials pages lazy-load offer cards on scroll.
    try:
        for _ in range(8):
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(600)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
    except Exception:
        pass

    # Scrolling can trigger a second batch of cards; give them a chance too.
    _wait_for_offer_content(page, timeout_ms=8000)

    # Reveal details hidden behind buttons/modals/accordions.
    _expand_and_collect_details(page)

    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    # Pull in offers that render inside iframes after everything has settled.
    _collect_iframe_text(page)


def _safe_content(page, retries: int = 5) -> str:
    """Return page.content(), retrying through the transient Playwright error
    'page is navigating and changing the content' that fires when the DOM is
    mid-navigation (common on dealer pages that client-side redirect)."""
    for attempt in range(retries):
        try:
            return page.content()
        except Exception:
            if attempt == retries - 1:
                return ""
            try:
                page.wait_for_timeout(1000)
            except Exception:
                return ""
    return ""


def fetch_rendered_html(url: str, timeout: int | None = None) -> str:
    """Load a URL with headless Playwright and return the rendered HTML."""
    timeout = timeout or 60

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=_headless(),
            args=_chromium_args(),
        )
        context = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1366, "height": 900},
            locale="en-US",
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', "
            "{get: () => undefined})"
        )

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout * 1000,
            )

            deadline = timeout * 1000
            waited = 0
            step = 3000
            reloaded = False

            while waited < deadline and _is_challenge(_safe_content(page)):
                page.wait_for_timeout(step)
                waited += step
                if not reloaded and waited >= deadline // 2:
                    reloaded = True
                    try:
                        page.reload(
                            wait_until="domcontentloaded",
                            timeout=timeout * 1000,
                        )
                    except Exception:
                        pass

            _load_dynamic_content(page)

            html = _safe_content(page)
            if _is_challenge(html):
                raise ScrapingError(
                    "Bot-protection challenge did not clear in Playwright."
                )
            return html
        finally:
            browser.close()


def fetch_html(url: str) -> str:
    """Fetch the rendered HTML with Playwright."""
    try:
        return fetch_rendered_html(url)
    except ScrapingError:
        raise
    except Exception as exc:
        raise ScrapingError(f"Playwright scrape failed: {exc}") from exc


def get_website_content_from_url(url: str) -> dict[str, str]:
    """Fetch the site and return title/header/body/footer visible text."""
    try:
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""

        header_tag = soup.find("header")
        header = (
            header_tag.get_text(separator="\n", strip=True)
            if header_tag
            else ""
        )

        footer_tag = soup.find("footer")
        footer = (
            footer_tag.get_text(separator="\n", strip=True)
            if footer_tag
            else ""
        )

        # Drop chrome so the body focuses on offer content, while still
        # including modal/dialog/disclaimer text that lives outside <main>.
        for tag in soup(["header", "footer", "nav"]):
            tag.decompose()

        container = soup.body or soup
        body = container.get_text(separator="\n", strip=True) if container else ""

        if not body.strip():
            raise ScrapingError("The website body was empty after extraction.")

        return {
            "url": url,
            "title": title,
            "header": header,
            "body": body,
            "footer": footer,
        }
    except ScrapingError:
        raise
    except Exception as exc:
        raise ScrapingError(f"Website extraction failed: {exc}") from exc
