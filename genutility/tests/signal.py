import os
import signal
import subprocess
import sys
from unittest.mock import Mock

from genutility.signal import HandleKeyboardInterrupt
from genutility.test import MyTestCase


class SignalTest(MyTestCase):
    def __init__(self, *args, **kwargs):
        MyTestCase.__init__(self, *args, **kwargs)

    def call(self, raise_after, a, b, c, d):
        try:
            with HandleKeyboardInterrupt(raise_after):
                try:
                    a()
                    signal.raise_signal(signal.SIGINT)
                    b()
                except KeyboardInterrupt:
                    c()
        except KeyboardInterrupt:
            d()

    def test_signal_test(self):
        a = Mock()
        b = Mock()
        c = Mock()
        try:
            a()
            signal.raise_signal(signal.SIGINT)
            b()
        except KeyboardInterrupt:
            c()
        a.assert_called_with()
        b.assert_not_called()
        c.assert_called_with()

    def test_real_ctrl_c_event_in_isolated_process(self):
        code = """
import os
import sys
import time
from genutility.os import interrupt
from genutility.signal import HandleKeyboardInterrupt

manager = HandleKeyboardInterrupt()
try:
    with manager:
        print("ready", flush=True)
        if os.name == "nt":
            from cwinsdk.um.consoleapi import PHANDLER_ROUTINE, SetConsoleCtrlHandler

            SetConsoleCtrlHandler(PHANDLER_ROUTINE(), False)
        interrupt()

        deadline = time.monotonic() + 5
        while manager.signal_received is None and time.monotonic() < deadline:
            time.sleep(0.01)
        if manager.signal_received is None:
            sys.exit("SIGINT was not delivered")
        print("continued", flush=True)
except KeyboardInterrupt:
    print("handled", flush=True)
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
            startupinfo.wShowWindow = 0  # SW_HIDE
            options["creationflags"] = subprocess.CREATE_NEW_CONSOLE
            options["startupinfo"] = startupinfo

        result = subprocess.run([sys.executable, "-c", code], **options)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("continued", result.stdout.splitlines())
        self.assertIn("handled", result.stdout.splitlines())

    def test_raise_after_true(self):
        a = Mock()
        b = Mock()
        c = Mock()
        d = Mock()
        self.call(True, a, b, c, d)
        a.assert_called_with()
        b.assert_called_with()
        c.assert_not_called()
        d.assert_called_with()

    def test_raise_after_false(self):
        a = Mock()
        b = Mock()
        c = Mock()
        d = Mock()
        self.call(False, a, b, c, d)
        a.assert_called_with()
        b.assert_called_with()
        c.assert_not_called()
        d.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
