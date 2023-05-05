# File: tests/test_blockscope.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-18
# Description: Tests for context-based clone detection approach of BlockScope.

# All results are from 'master' branch, True = patch applied, False = still vulnerable
test_cases = [
    # BTC CVE-2021-3401
    ("bitcoin", "CVE-2021-3401", "bitcoin-abc", "2023-05-03", [(True,)]),
    ("bitcoin", "CVE-2021-3401", "BTCGPU", "2023-05-03", [(False,)]),
    ("bitcoin", "CVE-2021-3401", "dash", "2023-05-03", [(True,)]),
    ("bitcoin", "CVE-2021-3401", "dogecoin", "2023-05-03", [(True,)]),
    ("bitcoin", "CVE-2021-3401", "litecoin", "2023-05-03", [(True,)]),
    ("bitcoin", "CVE-2021-3401", "Ravencoin", "2023-05-03", [(True,)]),
    # BTC CVE-2018-17144
    ("bitcoin", "CVE-2018-17144", "BTCGPU", "2023-05-03", [(True,)]),
    ("bitcoin", "CVE-2018-17144", "dash", "2023-05-03", [(True,)]),
    ("bitcoin", "CVE-2018-17144", "dogecoin", "2023-05-03", [(True,)]),
    # ETH CVE-2022-29177
    ("go-ethereum", "CVE-2022-29177", "bor", "2023-05-03", [(True,)]),
    ("go-ethereum", "CVE-2022-29177", "bsc", "2023-05-03", [(True,)]),
    ("go-ethereum", "CVE-2022-29177", "celo-blockchain", "2023-05-03", [(True,)]),
    ("go-ethereum", "CVE-2022-29177", "optimism", "2023-05-03", [(False,)]),
    # ETH CVE-2020-26240
    ("go-ethereum", "CVE-2020-26240", "bor", "2023-05-03", [(True,)]),
    ("go-ethereum", "CVE-2020-26240", "bsc", "2023-05-03", [(True,)]),
    ("go-ethereum", "CVE-2020-26240", "optimism", "2023-05-03", [(False,)]),
]
