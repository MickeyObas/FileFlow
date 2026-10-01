from rq import Worker

from app.worker import tasks  # noqa: F401 — register task module
from app.worker.queue import QUEUE_NAME, get_redis_connection


def main() -> None:
    worker = Worker([QUEUE_NAME], connection=get_redis_connection())
    worker.work()


if __name__ == "__main__":
    main()
