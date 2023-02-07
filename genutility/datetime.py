from datetime import datetime
from datetime import time as dtime
from datetime import timedelta, timezone
from typing import Optional, overload

utcmin = datetime.min.replace(tzinfo=timezone.utc)
utcmax = datetime.max.replace(tzinfo=timezone.utc)


def current_local_timezone() -> timezone:
    """Returns a local fixed offset timezone.
    Warning: This timezone is only valid at the time of creation.
    Ie. if called in the summer for a local timezone which follows DST,
    and applied on a winter datetime, the result will be wrong.
    For a correct implementation use something like `dateutil.tz.tzlocal()` or `tzlocal.get_localzone()`.
    """

    return datetime.now(timezone.utc).astimezone().tzinfo


def is_aware(dt: datetime) -> bool:
    """Test if a datetime object is aware or naive."""

    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def naive_to_aware(dt, tzinfo=timezone.utc) -> datetime:
    if is_aware(dt):
        return dt
    else:
        return dt.replace(tzinfo=tzinfo)


def now(aslocal: bool = False) -> datetime:
    """Returns the current datetime as timezone aware object in
    UTC timezone if `aslocal=False` (the default)
    or local timezone if `aslocal=True`.
    """

    dt = datetime.now(timezone.utc)
    if aslocal:
        dt = dt.astimezone(None)
    return dt


def datetime_from_utc_timestamp(epoch: float, aslocal: bool = False) -> datetime:
    """Converts a UNIX epoch time in seconds to a timezone aware datetime.
    Negative values are supported and return a datetime counted backwards
    from 1970-01-01 UTC.
    `aslocal=True` doesn't work for negative values on Windows.
    """

    # don't use `fromtimestamp`, to have better cross platform support
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=epoch)

    if aslocal:
        dt = dt.astimezone(None)
    return dt


def datetime_from_utc_timestamp_ms(epoch: int, aslocal: bool = False) -> datetime:
    """Converts a UNIX epoch time in milliseconds to a timezone aware datetime.
    Negative values are supported and return a datetime counted backwards
    from 1970-01-01 UTC.
    `aslocal=True` doesn't work for negative values on Windows.
    """

    seconds, ms = divmod(epoch, 1000)

    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds, milliseconds=ms)

    if aslocal:
        dt = dt.astimezone(None)

    return dt


def datetime_from_utc_timestamp_ns(epoch: int, aslocal: bool = False) -> datetime:
    """Converts a UNIX epoch time in nano seconds to a timezone aware datetime.
    Negative values are supported and return a datetime counted backwards
    from 1970-01-01 UTC.
    `aslocal=True` doesn't work for negative values on Windows.
    """

    seconds, ns = divmod(epoch, 1000000000)

    # don't use `fromtimestamp`, to have better cross platform support
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds, microseconds=ns // 1000)

    if aslocal:
        dt = dt.astimezone(None)

    return dt


@overload
def between(dt: datetime, start: Optional[datetime], end: Optional[datetime]) -> bool:
    pass


@overload
def between(dt: dtime, start: Optional[dtime], end: Optional[dtime]) -> bool:
    pass


def between(dt, start=None, end=None):
    """Tests if `dt` is in-between `start` and `end` (inclusive and optionally open ended).

    If the parameters are datetimes, they all most be either offset-aware or native.
    If `start` and `end` are `time` objects (without dates),
    then `end` can come before `start` to specify ranges which overlap two days.

    If `start` equals `end`, return `True`.
    """

    if start and end:
        if start < end:
            return start <= dt and dt <= end
        else:
            return start <= dt or dt <= end

    if start and dt < start:
        return False
    if end and dt > end:
        return False
    return True
