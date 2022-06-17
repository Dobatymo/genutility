from __future__ import generator_stop

import sys
from types import FrameType
from typing import Any, Optional

""" All functions of this module use implemention details specific to CPython
    and might not work on other implementations.
"""


def find_local_in_call_stack(funcname: str, varname: str, stacklevel: int = 2) -> Any:

    """Finds a local variable by name `varname` by going up the call stack,
    looking for functions called `funcname`.

    The functions starts by looking at the calling frame of the calling point of this function by default.
    It can start a different point in the stack be changing `stacklevel`.
    Raises a KeyError if the variable cannot be found.

    Example:
            def func_a():
                    var_a = "asd"
                    func_b()

            def func_b():
                    # starts by looking at func_a and then going further up the stack
                    var_a = find_local_in_call_stack("func_a", "var_a")
                    assert var_a == "asd"

            func_a()
    """

    frame: Optional[FrameType] = sys._getframe(stacklevel)
    while frame:
        if frame.f_code.co_name == funcname and varname in frame.f_locals:
            return frame.f_locals[varname]
        frame = frame.f_back

    raise KeyError(f"Did not find variable {varname} in function {funcname}")
