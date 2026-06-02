from __future__ import annotations

from redis import Redis
from rq import Worker

from repomind.core.config import get_settings
from repomind.core.jobs import QUEUE_NAME


def main() -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REPOMIND_REDIS_URL is required to start an analysis worker.")
    worker = Worker([QUEUE_NAME], connection=Redis.from_url(settings.redis_url))
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
