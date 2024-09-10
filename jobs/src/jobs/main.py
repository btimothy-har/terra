import asyncio

from scrapers import NewsScraper
from scrapers import init_db

# def get_event_loop():
#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#     return loop


class JobsOrchestrator:
    def __init__(self):
        self.scrapers = []

    def add_scraper(self, scraper):
        self.scrapers.append(scraper)

    async def start(self):
        while True:
            tasks = []

            for scraper in self.scrapers:
                if scraper.should_run:
                    tasks.append(asyncio.create_task(scraper.run()))

            await asyncio.gather(*tasks)
            await asyncio.sleep(60)

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        self.loop.close()


async def main():
    await init_db()
    orchestrator = JobsOrchestrator()

    orchestrator.add_scraper(NewsScraper())
    await orchestrator.start()


if __name__ == "__main__":
    asyncio.run(main())
