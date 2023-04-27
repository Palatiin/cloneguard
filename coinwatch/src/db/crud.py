# crud.py

import typing as t
from typing import List

from sqlalchemy.orm import Session

from coinwatch.src.db.declarative_base import SchemaBase
from coinwatch.src.db.schema import Bug, Detection, Project

ModelType = t.TypeVar("ModelType", bound=SchemaBase)


class CRUDBase(t.Generic[ModelType]):
    def __init__(self, model: t.Type[ModelType]):
        self.model = model

    def count(self, db: Session) -> int:
        return db.query(self.model).count()

    def create(self, db: Session, obj: ModelType) -> ModelType:  # noqa
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get(self, db: Session, id_: int) -> t.Optional[ModelType]:
        return db.query(self.model).filter_by(id=id_).first()

    def get_all(self, db: Session) -> t.List[ModelType]:
        return db.query(self.model).all()

    def update(self, db: Session, db_obj: ModelType) -> ModelType:  # noqa
        db.commit()
        return db_obj

    def delete(self, db: Session, obj: ModelType) -> t.Optional[ModelType]:  # noqa
        db.delete(obj)
        db.commit()
        return obj


class CRUDBug(CRUDBase[Bug]):
    def get_cve(self, db: Session, cve: str) -> t.Optional[ModelType]:
        return db.query(self.model).filter_by(cve_id=cve).first()

    def get_verified(self, db: Session, verified: bool) -> t.List[ModelType]:
        return db.query(self.model).filter_by(verified=verified).all()


class CRUDProject(CRUDBase[Project]):
    def get_by_name(self, db: Session, name: str) -> t.Optional[ModelType]:
        return db.query(self.model).filter_by(name=name).first()

    def get_all_clones(self, db: Session, source: ModelType) -> t.List[ModelType]:
        return db.query(self.model).filter_by(parent_id=source.id).all()

    def get_all_watched(self, db: Session) -> t.List[ModelType]:
        return db.query(self.model).filter_by(watch=True).all()


class CRUDDetection(CRUDBase[Detection]):
    def create(self, db: Session, obj: ModelType) -> ModelType:
        if _obj := self.get_by_bug_and_project_id(db, obj.bug, obj.project):
            return _obj
        return super().create(db, obj)

    def get_by_bug_and_project_id(self, db: Session, bug_id: int, project_id: int):
        return db.query(self.model).filter_by(bug=bug_id, project=project_id).first()

    def get_all_after(self, db: Session, timestamp: int) -> List[ModelType]:
        return db.query(self.model).filter(self.model.timestamp > timestamp).all()


bug = CRUDBug(Bug)
project = CRUDProject(Project)
detection = CRUDDetection(Detection)
