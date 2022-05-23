from __future__ import generator_stop

from datetime import datetime as _datetime
from datetime import timezone

try:
    _datetime.fromisoformat  # New in version 3.7
    datetime = _datetime

except AttributeError:

    import re
    from datetime import timedelta

    from ..string import tryint

    isoformatre = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.(\d{6}))?(\+|-)(\d{2}):(\d{2})$")
    isoformatre2 = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

    class datetime(_datetime):  # type: ignore[no-redef]
        @classmethod
        def fromisoformat(cls, date_string):
            # (str, ) -> datetime

            """Converts an ISO 8601 date and time with timezone string to a timezone aware datetime.
            eg. '2019-03-01T11:30:01.123000+00:00'
            eg. '2019-02-02T12:30:02.456000+04:00'
            eg. '2019-01-03T22:30:03.789000-07:00'
            """

            m = isoformatre.match(date_string)

            if m:
                groups = m.groups()
                year, month, day, hour, minute, second, milliseconds, tzsign, tzhours, tzminutes = map(tryint, groups)
            else:
                groups = isoformatre2.match(date_string).groups()
                year, month, day = map(tryint, groups)
                hour, minute, second, milliseconds, tzsign, tzhours, tzminutes = (0, 0, 0, 0, "+", 0, 0)

            offset = timedelta(hours=tzhours, minutes=tzminutes)

            if tzsign == "-":
                offset = -offset

            if milliseconds is None:
                milliseconds = 0

            return cls(year, month, day, hour, minute, second, milliseconds, tzinfo=timezone(offset))
