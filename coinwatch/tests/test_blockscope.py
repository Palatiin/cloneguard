# test_blockscope.py

# All results are from 'master' branch, True = patch applied, False = still vulnerable
test_cases = [
    # BTC CVE-2021-3401
    ("bitcoin", "CVE-2021-3401", "dogecoin", "2023-04-03", [(True, 1.2057101364328597)]),
    # digibyte - applied the patch, but also did a refactoring so that upper context is missing - no detection
    # ("bitcoin", "CVE-2021-3401", "digibyte", "2023-04-03", [(False, 1.3927835488658045)]),
    ("bitcoin", "CVE-2021-3401", "dash", "2023-04-03", [(True, 1.3364258920974925)]),
    ("bitcoin", "CVE-2021-3401", "Ravencoin", "2023-04-03", [(True, 1.132656831022397)]),
    ("bitcoin", "CVE-2021-3401", "BTCGPU", "2023-04-03", [(False, 1.539621014964216)]),
    # ETH CVE-2022-29177
    ("go-ethereum", "CVE-2022-29177", "optimism", "2023-04-03", [(False, 1.9523809523809523)]),
    ("go-ethereum", "CVE-2022-29177", "bsc", "2023-04-03", [(True, 1.9523809523809523)]),
    # ETH CVE-2020-26265
    ("go-ethereum", "CVE-2020-26265", "optimism", "2023-04-03", [(False, 1.95)]),
    ("go-ethereum", "CVE-2020-26265", "bsc", "2023-04-03", [(True, 1.6349747474747476)]),
    # ETH CVE-2020-26240
    ("go-ethereum", "CVE-2020-26240", "optimism", "2023-04-08", [(False, 1.6329028461959496)]),
    ("go-ethereum", "CVE-2020-26240", "bsc", "2023-04-08", [(True, 1.3861887367323171)]),
    # BTC CVE-2019-15947 PatchType.ADD
    ("bitcoin", "CVE-2019-15947", "dogecoin", "2023-04-08", [(True, 0.6909502044060868)]),
    ("bitcoin", "CVE-2019-15947", "litecoin", "2023-04-08", [(True, 0.6909502044060868)]),
    ("bitcoin", "CVE-2019-15947", "zcash", "2023-04-08", [(True, 0.6909502044060868)]),
    ("bitcoin", "CVE-2019-15947", "digibyte", "2023-04-08", [(True, 0.6909502044060868)]),
    ("bitcoin", "CVE-2019-15947", "dash", "2023-04-08", [(True, 0.6909502044060868)]),
    ("bitcoin", "CVE-2019-15947", "Ravencoin", "2023-04-08", [(True, 0.6909502044060868)]),
    ("bitcoin", "CVE-2019-15947", "BTCGPU", "2023-04-08", [(False, 2.0)]),  # similarity of contexts
    # BTC CVE-2018-17145
    ("bitcoin", "CVE-2018-17145", "dash", "2023-04-08", [(True, 1.4395524955436718)]),
    ("bitcoin", "CVE-2018-17145", "Ravencoin", "2023-04-08", [(True, 1.5997935091868916)]),
    ("bitcoin", "CVE-2018-17145", "BTCGPU", "2023-04-08", [(True, 2.0)]),
]
