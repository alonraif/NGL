import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.grading import GradingParser


class GradingParserTests(unittest.TestCase):
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

    def test_grading_events(self):
        lines = [
            "2024-04-01 10:00:00+00:00: INFO:ModemGrading: changed grade of modem 3 from Full Service to Limited Service",
            "2024-04-01 10:00:05+00:00: INFO:modem 3 extrapolated smooth rtt (572) or upstreamdelay (560) NOT good enough for full service",
            "2024-04-01 10:00:10+00:00: INFO:modem 3 loss ( 46 ) above full service ceil 25",
            "2024-04-01 10:00:15+00:00: INFO:ModemGrading: changed grade of modem 3 from Limited Service to Full Service",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = GradingParser('grading')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertEqual(len(parsed), 4)
            self.assertEqual(parsed[0]['status'], 'Limited Service')
            self.assertIn('rtt', parsed[1]['detail'])
            self.assertIn('loss', parsed[2]['detail'])
            self.assertEqual(parsed[3]['status'], 'Full Service')
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
