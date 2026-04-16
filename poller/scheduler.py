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
    log.critical(f'All retries exhausted for {poll_fn.__name__}')

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
    
    log.info("Running initial bootstrap poll...")
    await run_poll_gdelt()
    await run_poll_rss()
    
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    asyncio.run(main())
