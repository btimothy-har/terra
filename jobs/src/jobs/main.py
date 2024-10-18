import argparse
import ast
import asyncio
import importlib
import signal
import sys

from jobs.config import init_ell
from jobs.database import init_db

cli = argparse.ArgumentParser(description="Job Orchestrator CLI")
cli.add_argument("job", help="Name of the job to run (e.g., news_graph).")
cli.add_argument(
    "--args", nargs=argparse.REMAINDER, help="Additional job-specific arguments."
)


def parse_args(args: list[str] | None = None) -> dict[str, str]:
    kwargs = dict()

    if not args:
        return kwargs

    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            try:
                kwargs[key] = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                kwargs[key] = value
    return kwargs


class JobsOrchestrator:
    def __init__(self):
        self.jobs = []
        self.running = True
        self.task = None
        self.iter_count = 0

    def add_job(self, job):
        self.jobs.append(job)

    async def run(self, job: str, args: list[str]):
        module = importlib.import_module(f"jobs.tasks.{job}")
        pipeline = module.Pipeline()
        kwargs = parse_args(args)

        await init_db()
        await pipeline.run(**kwargs)


async def shutdown(signal, loop):
    print(f"Received {signal.name}, shutting down...")
    loop.stop()
    sys.exit(0)


async def main():
    await init_ell()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )
    args = cli.parse_args()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )

    if len(args.job):
        orchestrator = JobsOrchestrator()
        await orchestrator.run(args.job, args.args)

    else:
        print("No job specified.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
