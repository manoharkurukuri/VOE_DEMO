# Tests

Test suite for the Vehicle Offer Extraction app, covering the API and every
module: broker, subscriber, scraper, LLM extractor, Excel service, schemas, and
the offer-generation workflow.

## Layout

| File | Covers | Type |
|------|--------|------|
| `test_broker.py` | `InMemoryBroker` pub/sub, workers, error handling | unit |
| `test_excel_service.py` | `ExcelService` file naming + workbook generation | unit |
| `test_schemas.py` | `VehicleIncentiveLLM` validators / parsing | unit |
| `test_workflow_dedup.py` | offer dedup + renumbering in the workflow | unit |
| `test_offer_generation_service.py` | zip/error-file assembly + full pipeline | unit + integration |
| `test_scraper.py` | HTML parsing helpers + live Playwright scrape | unit + integration |
| `test_llm_extractor.py` | key handling + live Gemini extraction | unit + integration |
| `test_subscriber.py` | `_RunTracker` timing + live broker pipeline | unit + integration |
| `test_api.py` | `/health`, `/api/v1/offers/generate` + live e2e | unit + integration |

## Running

Install dev dependencies (into a virtualenv) and the Playwright browser:

```bash
python -m venv venv
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m playwright install chromium
```

Fast unit tests (no network, no API key):

```bash
./venv/bin/python -m pytest -m "not integration"
```

Live integration tests hit real services (the live dealer page via Playwright
and the Gemini LLM). They need network access and a Gemini API key in `.env`:

```bash
# .env
GEMINI_API_KEY=your-key-here
```

```bash
./venv/bin/python -m pytest -m integration
```

Integration tests that need the key are skipped automatically when it is not
configured. Live assertions are structural (non-empty body, `offers` is a list,
a workbook/zip is produced) rather than exact values, because live page content
changes over time.
