import logging
from typing import Callable, Iterable, Iterator, List, Tuple

from typing_extensions import Self

from ..exceptions import MalformedFile
from ..file import PathType

REAL_FILM_FPS = 24.0
NTSC_PROG_FPS = 24000.0 / 1001
NTSC_VIDEO_FPS = 30000.0 / 1001
PAL_PROG_FPS = 25.0
PAL_VIDEO_FPS = 30.0

DEFAULT_ENCODING = "utf-8-sig"


def ntsc_to_pal(num) -> float:
    return num * NTSC_PROG_FPS / PAL_PROG_FPS


def pal_to_ntsc(num) -> float:
    return num * PAL_PROG_FPS / NTSC_PROG_FPS


def film_to_ntsc(num) -> float:
    return num * REAL_FILM_FPS / NTSC_PROG_FPS


def to_msec(s: str) -> int:
    h, m, s, ms = (int(i) for i in s.replace(",", ":").replace(".", ":").split(":"))
    return (h * 60 * 60 + m * 60 + s) * 1000 + ms


def to_srt_time(t: int) -> str:
    r, ms = divmod(t, 1000)
    r, s = divmod(r, 60)
    h, m = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(ms):03d}"


class Subtitle:
    def __init__(self) -> None:
        self.num = 0
        self.start = 0
        self.end = 0
        self.lines: List[str] = []

    def get_times(self) -> Tuple[str, str]:
        return to_srt_time(self.start), to_srt_time(self.end)

    def set_times(self, start: str, end: str) -> None:
        self.start, self.end = to_msec(start), to_msec(end)

    def append(self, line: str) -> None:
        self.lines.append(line)


class SRTFile:
    nl = "\n"
    sep = " --> "

    def __init__(
        self, filename: PathType, mode: str = "r", encoding: str = DEFAULT_ENCODING, overwrite_index: bool = False
    ) -> None:
        self.state = 0
        self.linenum = 0
        self.sub_num = 0
        self.fp = open(filename, mode, encoding=encoding, errors="replace")
        self.overwrite_index = overwrite_index

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self) -> None:
        self.fp.close()

    def write_subtitle(self, subtitle: Subtitle) -> None:
        start, end = subtitle.get_times()
        if self.overwrite_index:
            self.fp.write(str(self.sub_num) + self.nl)
        else:
            self.fp.write(str(subtitle.num) + self.nl)
        self.fp.write(start + self.sep + end + self.nl)
        for line in subtitle.lines:
            self.fp.write(line)
            self.fp.write(self.nl)
        self.fp.write(self.nl)
        self.sub_num += 1

    def read_line(self) -> None:
        self.linenum += 1
        line = next(self.fp).rstrip()

        try:
            if self.state == 0:
                self.sub.num = int(line)
                self.state = 1
            elif self.state == 1:
                start, end = line.split(self.sep)
                self.sub.set_times(start, end)
                self.state = 2
            elif self.state == 2:
                if line == "":
                    self.state = 0
                else:
                    self.sub.append(line)
        except ValueError:
            raise MalformedFile(f"Error in line {self.linenum}: srt malformed: {line!r}")

    def read_subtitle(self) -> Subtitle:
        self.sub = Subtitle()
        self.read_line()
        while self.state != 0:
            self.read_line()  # can throw, and leave incomplete subtitle in buffer (eg. if file doesn't end in newline)
        return self.sub

    def __iter__(self):
        if self.fp:
            return self
        else:
            raise ValueError("I/O operation on closed file.")

    def __next__(self) -> Subtitle:
        return self.read_subtitle()


def transform(
    infile: PathType, outfile: PathType, callback: Callable[[Subtitle], Subtitle], encoding: str = DEFAULT_ENCODING
) -> None:
    with SRTFile(infile, "r", encoding) as fi, SRTFile(outfile, "w", encoding) as fo:
        for subtitle in fi:
            subtitle = callback(subtitle)
            fo.write_subtitle(subtitle)


def merge(srtlines: Iterable[str], lim: str) -> List[str]:
    ret: List[str] = []
    for line in srtlines:
        if line.startswith(lim):
            ret.append(line[len(lim) :])
        else:
            if not ret:
                ret.append(line)
            else:
                ret[-1] = ret[-1] + " " + line
    return ret


def srt2txt(srt_fp) -> Iterator[str]:
    lim = "- "
    pos = 0
    lines: List[str] = []

    while True:
        if pos >= len(lines):
            sub = next(srt_fp)
            lines = merge(sub.lines, lim)
            pos = 0
        ret = lines[pos]
        pos += 1
        yield ret


def compare_srt_and_txt(srt_file, txt_file) -> Iterator[Tuple[str, str]]:
    with SRTFile(srt_file, "r", encoding="utf-8-sig") as srt, open(txt_file, encoding="utf-8-sig") as txt:
        srtiter = srt2txt(srt)

        limit = 10

        while limit > 0:
            try:
                line = next(txt).rstrip()
                if not line:
                    continue
                if not line.startswith("- "):
                    print(line)
                else:
                    line = line[2:]
                    start = 0
                    while start <= len(line):
                        srtpart = next(srtiter)
                        txtpart = line[start : start + len(srtpart)]
                        logging.debug(f"Compare '{txtpart}' '{srtpart}'")
                        if txtpart != srtpart:
                            # print("{} - {}".format(sub.start, sub.end))
                            yield (txtpart, srtpart)
                            limit -= 1
                        start += len(srtpart) + 1
            except StopIteration:
                break
