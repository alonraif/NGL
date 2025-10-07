import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.sessions_native import SessionsParser


class SessionsParserTests(unittest.TestCase):
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

    def test_sessions_parsing(self):
        lines = [
            "2024-04-01 10:00:00+00:00: >>> Stream start (Collecting)",
            "2024-04-01 10:30:00+00:00: ~~> Stream stop (Collecting)",
            "2024-04-01 11:00:00+00:00: >>> Stream start (Collecting)",
            "2024-04-01 11:15:00+00:00: INFO: session id: ABC123",
            "2024-04-01 11:45:00+00:00: ~~> Stream stop (Collecting)",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = SessionsParser('sessions')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertEqual(len(parsed), 2)
            first, second = parsed
            self.assertEqual(first['status'], 'Complete')
            self.assertEqual(second['session_id'], 'ABC123')
            self.assertEqual(second['status'], 'Complete')
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
