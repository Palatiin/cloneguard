# db_init.py

from datetime import datetime as dt

import coinwatch.src.db.crud as crud
from coinwatch.db.schema import *


def init(db):
    project = crud.project.create(
        db,
        Project(
            id=1, url="git@github.com:bitcoin/bitcoin.git", name="bitcoin", author="bitcoin", language="cpp", watch=True
        ),
    )
    child = crud.project.create(
        db,
        Project(
            id=2,
            url="git@github.com:test/test.git",
            name="test",
            author="test",
            language="cpp",
            watch=False,
            parent_id=project.id,
        ),
    )
    bug = crud.bug.create(
        db,
        Bug(
            id=1, cve_id="CVE-2018-17144", fix_commit='["d1dee205473140aca34180e5de8b9bbe17c2207d"]', project=project.id
        ),
    )
    detection = crud.detection.create(
        db, Detection(id=1, timestamp=dt.now(), confidence=1.0, bug=bug.id, project=child.id)
    )
