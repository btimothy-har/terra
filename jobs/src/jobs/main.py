import asyncio
import signal
import sys

from scrapers import NewsScraper
from scrapers import init_db


class JobsOrchestrator:
    def __init__(self):
        self.scrapers = []
        self.running = True
        self.task = None
        self.iter_count = 0

    def add_scraper(self, scraper):
        self.scrapers.append(scraper)

    async def _loop(self):
        while self.running:
            if self.iter_count > 0:
                await asyncio.sleep(60)

            tasks = []
            for scraper in self.scrapers:
                tasks.append(asyncio.create_task(scraper.run()))

            await asyncio.gather(*tasks)
            self.iter_count += 1

    async def start(self):
        self.task = asyncio.create_task(self._loop())
        await self.task

    def stop(self):
        self.running = False


async def shutdown(signal, loop, orchestrator):
    print(f"Received {signal.name}, shutting down...")
    orchestrator.stop()
    loop.stop()
    sys.exit(0)


async def main():
    loop = asyncio.get_running_loop()
    await init_db()
    orchestrator = JobsOrchestrator()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop, orchestrator))
        )

    orchestrator.add_scraper(NewsScraper())
    await orchestrator.start()


if __name__ == "__main__":
    asyncio.run(main())
