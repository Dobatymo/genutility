from datetime import datetime, time, timezone

from genutility.datetime import between, datetime_from_utc_timestamp, datetime_from_utc_timestamp_ms
from genutility.test import MyTestCase, parametrize


class DatetimeTest(MyTestCase):
    @parametrize((0, datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc)))
    def test_datetime_from_utc_timestamp(self, input, truth):
        result = datetime_from_utc_timestamp(input)
        self.assertEqual(result, truth)

    @parametrize((0, datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc)))
    def test_datetime_from_utc_timestamp_ms(self, input, truth):
        result = datetime_from_utc_timestamp_ms(input)
        self.assertEqual(result, truth)

    @parametrize(
        (time(12), time(11), time(13), True),
        (time(12), time(13), time(11), False),
        (time(12), time(15), time(13), True),
        (time(12), time(13), time(15), False),
        (time(12), time(11), time(9), True),
        (time(12), time(9), time(11), False),
        (time(11), time(11), time(13), True),
        (time(13), time(11), time(13), True),
        (time(15), time(15), time(13), True),
        (time(13), time(15), time(13), True),
        (time(13), time(0), time(0), True),
        (
            datetime(1970, 1, 2, tzinfo=timezone.utc),
            datetime(1970, 1, 1, tzinfo=timezone.utc),
            datetime(1970, 1, 3, tzinfo=timezone.utc),
            True,
        ),
        (datetime(1970, 1, 2, tzinfo=timezone.utc), datetime(1970, 1, 1, tzinfo=timezone.utc), None, True),
        (datetime(1970, 1, 2, tzinfo=timezone.utc), None, datetime(1970, 1, 3, tzinfo=timezone.utc), True),
        (
            datetime(1970, 1, 3, tzinfo=timezone.utc),
            datetime(1970, 1, 1, tzinfo=timezone.utc),
            datetime(1970, 1, 2, tzinfo=timezone.utc),
            False,
        ),
        (datetime(1970, 1, 1, tzinfo=timezone.utc), datetime(1970, 1, 2, tzinfo=timezone.utc), None, False),
        (datetime(1970, 1, 3, tzinfo=timezone.utc), None, datetime(1970, 1, 2, tzinfo=timezone.utc), False),
    )
    def test_between(self, dt, start, end, truth):
        result = between(dt, start, end)
        self.assertEqual(result, truth)


if __name__ == "__main__":
    import unittest

    unittest.main()
