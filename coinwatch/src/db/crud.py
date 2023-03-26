# crud.py

import typing as t

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
        return db.query(self.model).filter(self.model.id == id_).first()

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
        return db.query(self.model).filter(self.model.cve_id == cve).first()

    def get_verified(self, db: Session, verified: bool) -> t.List[ModelType]:
        return db.query(self.model).filter(self.model.verified == verified).all()


class CRUDProject(CRUDBase[Project]):
    def get_by_name(self, db: Session, name: str) -> t.Optional[ModelType]:
        return db.query(self.model).filter(self.model.name == name).first()

    def get_all_clones(self, db: Session, source: ModelType) -> t.List[ModelType]:
        return db.query(self.model).filter(self.model.parent_id == source.id).all()


class CRUDDetection(CRUDBase[Detection]):
    ...


bug = CRUDBug(Bug)
project = CRUDProject(Project)
detection = CRUDDetection(Detection)
