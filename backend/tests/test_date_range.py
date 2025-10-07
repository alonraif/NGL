import datetime
import unittest

from backend.parsers.base import DateRange


class DateRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import dateutil.parser  # noqa: F401
            import pytz  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("dateutil/pytz not available in test environment")

    def test_contains_with_timezone_conversion(self):
        dr = DateRange(start="2024-01-01 10:00:00-05:00", end="2024-01-01 12:00:00-05:00")

        aware = datetime.datetime(2024, 1, 1, 15, 0, tzinfo=datetime.timezone.utc)
        self.assertTrue(dr.contains(aware))

    def test_excludes_before_start(self):
        dr = DateRange(start="2024-01-01T00:00:00Z")
        dt = datetime.datetime(2023, 12, 31, 23, 59, tzinfo=datetime.timezone.utc)
        self.assertFalse(dr.contains(dt))

    def test_excludes_after_end(self):
        dr = DateRange(end="2024-01-02T00:00:00Z")
        dt = datetime.datetime(2024, 1, 2, 0, 0, 1, tzinfo=datetime.timezone.utc)
        self.assertFalse(dr.contains(dt))

    def test_naive_datetime_localized(self):
        dr = DateRange(start="2024-01-01T00:00:00Z", end="2024-01-02T00:00:00Z")
        dt = datetime.datetime(2024, 1, 1, 12, 0)  # naive
        self.assertTrue(dr.contains(dt))


if __name__ == "__main__":
    unittest.main()
