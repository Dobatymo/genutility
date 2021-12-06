def contains_digit_2(s):
    # type: (str, ) -> bool

    return any(i.isdigit() for i in s)


first = "1" + "a" * 100000
last = "a" * 100000 + "1"

benchmarks = {
    "contains_digit": {
        "first": {
            "stmt": "contains_digit(first)",
            "setup": "from genutility.string import contains_digit; from __main__ import first",
            "number": 1000,
        },
        "last": {
            "stmt": "contains_digit(last)",
            "setup": "from genutility.string import contains_digit; from __main__ import last",
            "number": 1000,
        },
    },
    "contains_digit_2": {
        "first": {
            "stmt": "contains_digit_2(first)",
            "setup": "from __main__ import contains_digit_2, first",
            "number": 1000,
        },
        "last": {
            "stmt": "contains_digit_2(last)",
            "setup": "from __main__ import contains_digit_2, last",
            "number": 1000,
        },
    },
}

if __name__ == "__main__":
    from genutility.benchmarks import run

    run(benchmarks)
