# File: utils/db_init.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-03-19
# Description: Database initialization script.

from datetime import datetime as dt

import cloneguard.src.db.crud as crud
from cloneguard.src.db.schema import *


def init(db):
    project = crud.project.create(
        db,
        Project(  # bitcoin
            id=1,
            url="https://github.com/bitcoin/bitcoin.git",
            name="bitcoin",
            author="bitcoin",
            language="cpp",
            watch=True,
        ),
    )
    child = crud.project.create(
        db,
        Project(  # dogecoin
            id=2,
            url="https://github.com/dogecoin/dogecoin.git",
            name="dogecoin",
            author="dogecoin",
            language="cpp",
            watch=False,
            parent_id=project.id,
        ),
    )
    bug = crud.bug.create(
        db,
        Bug(id=1, cve_id="CVE-2018-17144", fix_commit='["d1dee20547"]', project=project.id),
    )
    detection = crud.detection.create(
        db, Detection(id=1, created=dt.now(), confidence=1.0, bug=bug.id, project=child.id)
    )

    # the rest of pre-cloned bitcoin forks
    crud.project.create(
        db,
        Project(  # litecoin
            id=3,
            url="https://github.com/litecoin-project/litecoin.git",
            name="litecoin",
            author="litecoin-project",
            language="cpp",
            parent_id=project.id,
        ),
    )

    crud.project.create(
        db,
        Project(  # zcash
            id=4,
            url="https://github.com/zcash/zcash.git",
            name="zcash",
            author="zcash",
            language="cpp",
            parent_id=project.id,
        ),
    )
