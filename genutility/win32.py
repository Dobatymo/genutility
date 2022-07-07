from __future__ import generator_stop

import logging
from datetime import datetime
from math import nan
from typing import Iterator, List, Tuple

import win32evtlog
import winerror
import wmi

logger = logging.getLogger(__name__)


class Resource:
    def __init__(self, wmii=None) -> None:
        if wmii:
            self.wmii = wmii
        else:
            self.wmii = wmi.WMI()

    def __iter__(self) -> "Resource":
        return self


class os_resources(Resource):
    def __next__(self) -> Tuple[int, int, int]:
        threads = 0
        handles = 0
        pagefaults = 0
        for proc in self.wmii.Win32_Process():
            threads += proc.ThreadCount
            handles += proc.HandleCount
            pagefaults += proc.PageFaults
        return threads, handles, pagefaults


class cpu_usage(Resource):
    def __init__(self, wmii=None, proc_name: str = "_Total") -> None:

        """proc_name is the name of the processor,
        default value mean across all processors.
        """

        Resource.__init__(self, wmii)
        self.proc_name = proc_name

        self.real0 = nan
        self.user0 = nan
        self.sys0 = nan
        self.ts0 = nan

    @staticmethod
    def get_proc_names(wmii) -> List[str]:
        return [proc.name for proc in wmii.Win32_PerfRawData_PerfOS_Processor()]

    def __next__(self) -> Tuple[float, float, float, float]:
        (p,) = self.wmii.Win32_PerfRawData_PerfOS_Processor(name=self.proc_name)

        real = int(p.PercentProcessorTime)
        user = int(p.PercentUserTime)
        sys = int(p.PercentPrivilegedTime)
        ts = int(p.Timestamp_Sys100NS)

        try:
            delta_time = ts - self.ts0
            real_ratio = 1 - (real - self.real0) / delta_time  # One Minus should not be necessary
            user_ratio = (user - self.user0) / delta_time
            sys_ratio = (sys - self.sys0) / delta_time
        except ZeroDivisionError:
            real_ratio = nan
            user_ratio = nan
            sys_ratio = nan

        self.real0 = real
        self.user0 = user
        self.sys0 = sys
        self.ts0 = ts

        return (real_ratio, user_ratio, sys_ratio, delta_time / 10000000)


class ram_usage(Resource):
    def __next__(self) -> float:
        (p,) = self.wmii.Win32_OperatingSystem()
        total = int(p.TotalVisibleMemorySize)
        free = int(p.FreePhysicalMemory)
        assert total > 0
        return 1 - (free / total)


class hdd_usage(Resource):
    def __next__(self) -> List[Tuple[str, float]]:
        ret = []
        for disk in self.wmii.Win32_LogicalDisk(DriveType=3):
            total = int(disk.Size)
            free = int(disk.FreeSpace)
            ret.append((disk.Caption, 1 - (free / total)))
        return ret


def event_logs(server: str = "localhost", source: str = "System") -> Iterator[dict]:

    """
    EventType: severity level

    EVENTLOG_ERROR_TYPE 0x0001
    EVENTLOG_WARNING_TYPE 0x0002
    EVENTLOG_INFORMATION_TYPE 0x0004
    EVENTLOG_AUDIT_SUCCESS 0x0008
    EVENTLOG_AUDIT_FAILURE 0x0010

    EventID: same for same class of messages, stringinserts are provides to template belonging to eventid

    """

    fields = {
        "Reserved",
        "RecordNumber",
        "TimeGenerated",
        "TimeWritten",
        "EventID",
        "EventType",
        "EventCategory",
        "ReservedFlags",
        "ClosingRecordNumber",
        "SourceName",
        "StringInserts",
        "Sid",
        "Data",
        "ComputerName",
    }
    fields = {
        "Reserved",
        "RecordNumber",
        "TimeGenerated",
        "TimeWritten",
        "EventID",
        "EventType",
        "EventCategory",
        "ReservedFlags",
        "ClosingRecordNumber",
        "SourceName",
        "StringInserts",
        "ComputerName",
    }

    # missing: "Sid", "Data"

    handle = win32evtlog.OpenEventLog(server, source)
    flags = win32evtlog.EVENTLOG_SEQUENTIAL_READ | win32evtlog.EVENTLOG_FORWARDS_READ

    logger.debug(f"Preparing to read {win32evtlog.GetNumberOfEventLogRecords(handle)} events")

    try:
        while True:
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            if events:
                for event in events:
                    ret = {f: getattr(event, f) for f in fields}
                    # does that work for different time zones?
                    ret["TimeGenerated"] = datetime.fromtimestamp(event.TimeGenerated.timestamp())
                    ret["TimeWritten"] = datetime.fromtimestamp(event.TimeWritten.timestamp())
                    if ret["StringInserts"]:
                        ret["StringInserts"] = ", ".join(ret["StringInserts"]).replace("\r\n", "\n")
                    if not ret["StringInserts"]:
                        ret["StringInserts"] = None
                    ret["EventID"] = winerror.HRESULT_CODE(ret["EventID"])
                    # print(ret)
                    yield ret
            else:
                break
    finally:
        win32evtlog.CloseEventLog(handle)


if __name__ == "__main__":
    from argparse import ArgumentParser
    from time import sleep

    from genutility.stdio import print_line

    parser = ArgumentParser(description="Monitor OS resource usage.")
    args = parser.parse_args()

    wmii = wmi.WMI()

    for a, b, c, d in zip(cpu_usage(wmii), ram_usage(wmii), hdd_usage(wmii), os_resources(wmii)):
        print("CPU:", a)
        print("RAM:", b)
        print("HDD:", c)
        print("OS:", d)
        print_line()
        sleep(1)
