# schemas.py

import datetime
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass


__all__ = ["VulnerabilityStatus", "Weakness", "Reference", "CVE"]


class VulnerabilityStatus(str, Enum):
    analyzed = "Analyzed"  # CVE-2013-4165
    modified = "Modified"  # CVE-2018-17144


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
