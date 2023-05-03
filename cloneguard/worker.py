# File: worker.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-28
# Description: RQ worker implementation.

import redis
from rq import Worker, Queue, Connection

from cloneguard.settings import REDIS_URL


listen = ["task_queue"]

if __name__ == "__main__":
    # connect to Redis server
    redis_conn = redis.Redis.from_url(REDIS_URL)
    with Connection(redis_conn):
        # start worker listening on task_queue
        worker = Worker(map(Queue, listen))
        worker.work()
