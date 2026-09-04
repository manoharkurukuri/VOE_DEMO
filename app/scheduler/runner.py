"""APScheduler-based per-type scheduler.

Runs in-process, started from the FastAPI lifespan only when
``settings.scheduler_enabled`` is true. Each offer type gets its own cron job that
publishes a scrape event for that type against the configured default workbook.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.scheduler_config import schedule_config
from app.core.config import settings
from app.core.logger import get_logger
from app.events.broker import scrape_broker
from app.events.run_lock import run_lock

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def _publish(offer_type_value: str) -> None:
    excel_path = settings.default_excel_path
    acquired, running = run_lock.acquire(offer_type_value)
    if not acquired:
        logger.warning(
            "[%s] Scheduler skipped: a run for '%s' is already in progress.",
            offer_type_value,
            running,
        )
        return
    logger.info(
        "[%s] Scheduler firing | excel_path=%s", offer_type_value, excel_path
    )
    scrape_broker.publish(
        {"excel_path": excel_path, "offer_type": offer_type_value}
    )


def start_scheduler() -> BackgroundScheduler | None:
    """Start the scheduler if enabled; return the running scheduler (or None)."""
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (set SCHEDULER_ENABLED=true to enable).")
        return None
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone=settings.app_timezone)
    for offer_type, cron_expr in schedule_config().items():
        scheduler.add_job(
            _publish,
            trigger=CronTrigger.from_crontab(cron_expr, timezone=settings.app_timezone),
            args=[offer_type.value],
            id=f"schedule_{offer_type.value}",
            replace_existing=True,
        )
        logger.info(
            "[%s] Scheduled job registered | cron=%s", offer_type.value, cron_expr
        )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started with %d jobs.", len(schedule_config()))
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")
