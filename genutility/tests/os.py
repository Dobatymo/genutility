import subprocess
import sys

from genutility.test import MyTestCase


class TestOS(MyTestCase):
    def test_interrupt(self):
        code = """
import os
import sys
import time

if os.name == "nt":
    from cwinsdk.um.consoleapi import PHANDLER_ROUTINE, SetConsoleCtrlHandler

    SetConsoleCtrlHandler(PHANDLER_ROUTINE(), False)

from genutility.os import interrupt

try:
    interrupt()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        time.sleep(0.01)
except KeyboardInterrupt:
    print("handled")
else:
    sys.exit("interrupt() did not raise KeyboardInterrupt")
"""
        options = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "timeout": 10,
        }
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            options["creationflags"] = subprocess.CREATE_NEW_CONSOLE
            options["startupinfo"] = startupinfo

        result = subprocess.run([sys.executable, "-c", code], **options)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["handled"], result.stdout.splitlines())


if __name__ == "__main__":
    import unittest

    unittest.main()
