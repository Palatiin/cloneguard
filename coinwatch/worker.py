# File: worker.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-28
# Description: Detection method worker

import os
import redis
from rq import Worker, Queue, Connection

listen = ["task_queue"]

if __name__ == "__main__":
    redis_conn = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen))
        worker.work()
