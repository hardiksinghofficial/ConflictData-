from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging
from poller.rss_poller import poll_rss
from poller.gdelt_poller import poll_gdelt
from poller.db_inserter import prune_old_events

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
log = logging.getLogger("scheduler")

async def poll_with_retry(poll_fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            await poll_fn()
            return
        except Exception as e:
            wait = 2 ** attempt
            log.error(f'Poll failed (attempt {attempt+1}): {e}')
            await asyncio.sleep(wait)
    log.warning(f'All retries exhausted for {poll_fn.__name__}, will retry on next schedule.')

async def run_poll_rss():
    await poll_with_retry(poll_rss)

async def run_poll_gdelt():
    await poll_with_retry(poll_gdelt)

async def main():
    log.info("Starting ConflictIQ Ingestion Poller...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_poll_rss, 'interval', minutes=2, max_instances=1)
    scheduler.add_job(run_poll_gdelt, 'interval', minutes=5, max_instances=1)
    scheduler.add_job(prune_old_events, 'cron', day_of_week='sun', hour=2)
    scheduler.start()

    # Wait for the API to fully start before running the bootstrap poll
    log.info("Waiting 15 seconds for API/DB to be ready before bootstrap poll...")
    await asyncio.sleep(15)

    log.info("Running initial bootstrap cleanup and poll...")
    try:
        from poller.db_inserter import retroactive_cleanup
        await retroactive_cleanup()
    except Exception as e:
        log.error(f"Retroactive cleanup failed: {e}")

    try:
        await run_poll_gdelt()
    except Exception as e:
        log.error(f"Bootstrap GDELT poll failed: {e}")
    try:
        await run_poll_rss()
    except Exception as e:
        log.error(f"Bootstrap RSS poll failed: {e}")

    log.info("Poller running. Waiting for scheduled jobs...")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        log.info("Poller shutting down.")

if __name__ == "__main__":
    asyncio.run(main())
