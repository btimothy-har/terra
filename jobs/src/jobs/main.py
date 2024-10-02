import argparse
import asyncio
import importlib
import signal
import sys

from jobs.database import init_db

cli = argparse.ArgumentParser(description="Job Orchestrator CLI")
cli.add_argument("jobs", nargs="*", help="List of job names to run (e.g., news_graph)")


class JobsOrchestrator:
    def __init__(self):
        self.jobs = []
        self.running = True
        self.task = None
        self.iter_count = 0

    def add_job(self, job):
        self.jobs.append(job)

    async def run(self, job: str):
        module = importlib.import_module(f"jobs.pipelines.{job}")
        pipeline = module.Pipeline()
        await init_db()

        await pipeline.run()


async def shutdown(signal, loop):
    print(f"Received {signal.name}, shutting down...")
    loop.stop()
    sys.exit(0)


async def main():
    loop = asyncio.get_running_loop()
    orchestrator = JobsOrchestrator()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )
    args = cli.parse_args()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )

    if args.jobs:
        tasks = [
            asyncio.create_task(orchestrator.run(job_name)) for job_name in args.jobs
        ]
        await asyncio.gather(*tasks)
    else:
        print("No jobs specified. Available jobs are:")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
