# cve.py

import datetime
import json
import os
import re
from collections import defaultdict
from typing import Dict, List, NoReturn, Optional

import requests

from coinwatch.settings import logger
from coinwatch.src.schemas import *


class CVEClient:
    """
    Client for CVE API.

    NOTE: currently limited to 5 RQ / rolling 30 sec time window, possible upgrade to 30/30

    https://nvd.nist.gov/developers/vulnerabilities
    """

    base_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    _re_cve = re.compile(r"(?=CVE-\d{4}-\d+$)")

    @staticmethod
    def _parse_output(data: Dict) -> Optional[CVE]:
        """
        Parse response from API into CVE data model.

        Args:
            data (Dict): CVE API response

        Returns:
            CVE data or None.
        """

        def _parse_descriptions(descriptions: List) -> Dict[str, List[str]]:
            descs = defaultdict(list)
            for description in descriptions:
                lang, value = description.values()
                descs[lang].append(value)
            return descs

        if data["totalResults"] == 0:
            return None
        if data["totalResults"] > 1:
            print("More than one CVE found")

        cve_data = data["vulnerabilities"][0]["cve"]

        descriptions = _parse_descriptions(cve_data["descriptions"])

        weaknesses = []
        for weakness in cve_data["weaknesses"]:
            weaknesses.append(
                Weakness(
                    source=weakness["source"],
                    type_=weakness["type"],
                    descriptions=_parse_descriptions(weakness["description"]),
                )
            )

        references = []
        for reference in cve_data["references"]:
            references.append(Reference(**reference))

        return CVE(
            id_=cve_data["id"],
            source_identifier=cve_data["sourceIdentifier"],
            published=datetime.datetime.fromisoformat(cve_data["published"]),
            last_modified=datetime.datetime.fromisoformat(cve_data["lastModified"]),
            vulnerability_status=cve_data["vulnStatus"],
            descriptions=descriptions,
            metrics=cve_data["metrics"],
            weaknesses=weaknesses,
            references=references,
            json=cve_data,
        )

    @staticmethod
    def load_cve_from_cache(cve: str) -> dict:
        with open(f"_cache/cve/{cve.upper()}", "r") as file:
            cve_data = "".join(file.readlines())
        return json.loads(cve_data)

    @staticmethod
    def save_cve_to_cache(cve: str, cve_data: str) -> NoReturn:
        with open(f"_cache/cve/{cve.upper()}", "w") as file:
            file.write(cve_data)

    def cve_id(self, cve: str) -> Optional[CVE]:
        """
        Fetch CVE data utilizing API param 'cveId'.

        Args:
            cve (str): CVE in format 'CVE-{year}-{id}'

        Returns:
            CVE data or None.
        """
        if not cve:
            return
        if not self._re_cve.match(cve):
            return

        if os.path.exists(f"_cache/cve/{cve.upper()}"):  # TMP - will be helpful for gathering stats for ref tags usage
            logger.info(f"clients: cve: Using cached data for {cve}.")
            return self._parse_output(self.load_cve_from_cache(cve))
        elif not os.path.exists("_cache/cve/"):
            os.mkdir("_cache/cve/")

        logger.info(f"clients: cve: Fetching {cve} from API.")
        response = requests.get(self.base_url, params={"cveId": cve})

        if response.status_code != 200:
            return

        self.save_cve_to_cache(cve, response.text)

        return self._parse_output(response.json())
