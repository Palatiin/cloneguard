# schema.py

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, List, Sequence, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from coinwatch.src.db.declarative_base import SchemaBase

Base = declarative_base()
metadata = Base.metadata

bug_id_sequence = Sequence("bug_id_sequence", start=100, data_type=Integer)
project_id_sequence = Sequence("project_id_sequence", start=100, data_type=Integer)
detection_id_sequence = Sequence("detection_id_sequence", start=100, data_type=Integer)


class Bug(Base):
    __tablename__ = "bug"

    id = Column(Integer(), bug_id_sequence, primary_key=True)
    cve_id = Column(String(16), nullable=True, default=None)
    fix_commit = Column(List[String], nullable=True, default=[])
    patch = Column(String(), nullable=True, default=None)
    verified = Column(Boolean(), nullable=False, default=False)

    project = relationship("Project", back_populates="bugs")
    detections = relationship("Detection", back_populates="bug")


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer(), project_id_sequence, primary_key=True)
    url = Column(String(256), nullable=False)
    name = Column(String(128), nullable=False)
    author = Column(String(128), nullable=False)
    language = Column(String(32))
    watch = Column(Boolean(), nullable=False, default=False)

    bugs = relationship("Bug", back_populates="project")
    detections = relationship("Detection", back_populates="project")


class Detection(Base):
    __tablename__ = "detection"

    id = Column(Integer(), detection_id_sequence, primary_key=True)
    timestamp = Column(DateTime(), nullable=False)
    confidence = Column(Float(), nullable=False)

    project = relationship("Project", back_populates="detections")
    bug = relationship("Bug", back_populates="detections")
