benchmarks = {
    "all_equal": {
        "all-different": {
            "stmt": "all_equal(range(100000))",
            "setup": "from genutility.iter import all_equal",
        },
        "all-same": {
            "stmt": "all_equal(range(100000))",
            "setup": "from itertools import repeat; from genutility.iter import all_equal",
        },
    },
    "last": {
        "few": {
            "stmt": "last(range(1))",
            "setup": "from genutility.iter import last",
        },
        "some": {
            "stmt": "last(range(10))",
            "setup": "from genutility.iter import last",
        },
        "many": {
            "stmt": "last(range(100000))",
            "setup": "from genutility.iter import last",
            "number": 1000,
        },
    },
    "lastdefault": {
        "few": {
            "stmt": "lastdefault(range(1))",
            "setup": "from genutility.iter import lastdefault",
        },
        "some": {
            "stmt": "lastdefault(range(10))",
            "setup": "from genutility.iter import lastdefault",
        },
        "many": {
            "stmt": "lastdefault(range(100000))",
            "setup": "from genutility.iter import lastdefault",
            "number": 1000,
        },
    },
}

if __name__ == "__main__":
    from genutility.benchmarks import run

    run(benchmarks)
