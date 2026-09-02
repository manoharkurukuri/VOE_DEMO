import logfire
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException
from app.core.config import settings  
from app.core.exception_handlers import register_exception_handlers
from app.api.offers import router as offers_router
from app.events.broker import extract_broker, scrape_broker
from app.events.subscriber import handle_extract_event, handle_scrape_event
from dotenv import load_dotenv

load_dotenv()

logfire.configure(
    service_name=settings.app_name,
    environment=settings.app_env,
    send_to_logfire="if-token-present",
)
logfire.instrument_pydantic(record="failure")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scrape_broker.subscribe(handle_scrape_event)
    extract_broker.subscribe(handle_extract_event)
    scrape_broker.start()
    extract_broker.start()
    yield
    scrape_broker.stop()
    extract_broker.stop()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(offers_router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logfire.info(
        "Incoming request",
        method=request.method,
        path=request.url.path,
    )
    return await call_next(request)

@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


