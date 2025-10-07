import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.memory import MemoryParser


class MemoryParserTests(unittest.TestCase):
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

    def test_memory_points(self):
        lines = [
            "2024-04-01 10:00:00+00:00: vic monitor (monitor/memorymonitor.py:32) INFO:Memory usage is 45.0% (900 MB out of 2000 MB)",
            "2024-04-01 10:05:00+00:00: corecard monitor (monitor/memorymonitor.py:32) WARNING:Memory usage is 80.0% (1600 MB out of 2000 MB)",
            "2024-04-01 10:10:00+00:00: server monitor (monitor/memorymonitor.py:31) INFO:Memory usage is 30.0% (1200 MB out of 4000 MB)",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = MemoryParser('memory')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertEqual(len(parsed), 3)
            self.assertEqual(parsed[0]['component'], 'VIC')
            self.assertFalse(parsed[0]['is_warning'])
            self.assertTrue(parsed[1]['is_warning'])
            self.assertEqual(parsed[1]['used_mb'], 1600.0)
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
