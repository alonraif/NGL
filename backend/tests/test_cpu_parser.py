import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.cpu import CpuParser


class CpuParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import dateutil.parser  # noqa: F401
            import pytz  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("dateutil/pytz not available")

    def _create_archive(self, lines):
        temp_dir = tempfile.TemporaryDirectory()
        log_path = Path(temp_dir.name) / "messages.log"
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        archive_path = Path(temp_dir.name) / "logs.tar"
        with tarfile.open(archive_path, "w") as tar:
            tar.add(log_path, arcname="messages.log")

        return temp_dir, archive_path

    def test_cpu_events(self):
        lines = [
            "2024-04-01 10:00:00+00:00: vic monitor INFO:CPU usage in detail is scputimes(user=7.1, idle=86.5, ...)",
            "2024-04-01 10:00:05+00:00: corecard monitor WARNING:CPU usage in detail is scputimes(user=7.1, idle=80.0, ...)",
            "2024-04-01 10:00:10+00:00: server monitor INFO:CPU usage is at 35.0%",
            "2024-04-01 10:00:12+00:00: vic monitor WARNING:CPU utilization on core 3 (index starts from 0) is high: scputimes(... idle=14.3)",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = CpuParser('cpu')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertEqual(len(parsed), 4)
            self.assertEqual(parsed[0]['component'], 'VIC')
            self.assertAlmostEqual(parsed[0]['idle_percent'], 86.5)
            self.assertEqual(parsed[2]['total_percent'], 35.0)
            self.assertEqual(parsed[3]['core_index'], 3)
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
