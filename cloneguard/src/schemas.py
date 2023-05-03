# File: src/schemas.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2022-08-08
# Description: Dataclasses for CVEs and other entities.

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


class VulnerabilityStatus(str, Enum):
    analyzed = "Analyzed"  # CVE-2013-4165
    modified = "Modified"  # CVE-2018-17144


class ReferenceType(str, Enum):
    undefined = "U"
    issue = "I"
    pull = "PR"
    release_notes = "RN"
    commit = "C"


@dataclass
class Weakness:
    source: str
    type_: str
    descriptions: Dict[str, List[str]]


@dataclass
class Reference:
    url: str
    source: str
    tags: List[str] = list
    body: str = str
    json: dict = dict
    type_: ReferenceType = ReferenceType.undefined


@dataclass
class CVE:
    id_: str
    source_identifier: str
    published: datetime.datetime
    last_modified: datetime.datetime
    vulnerability_status: VulnerabilityStatus
    descriptions: Dict[str, List[str]]
    metrics: Dict
    weaknesses: List[Weakness]
    references: List[Reference]
    json: Dict


@dataclass
class Sentence:
    filename: str
    file_extension: str
    line_number: int
    sentence: str


@dataclass
class TargetContext:
    key_statements: Tuple[Sentence, Sentence]
    boundary: List[Tuple[Tuple[int, int], Tuple[int, int]]]
    upper_code: List[Tuple[int, str]] = field(default_factory=list)
    lower_code: List[Tuple[int, str]] = field(default_factory=list)
    similarity: float = 0.0


@dataclass
class CandidateCode:
    context: TargetContext
    code: List[str]
