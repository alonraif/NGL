import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.databridge_bandwidth import DataBridgeBandwidthParser


class DataBridgeBandwidthParserTests(unittest.TestCase):
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

    def test_parses_databridge_rows(self):
        lines = [
            "2024-04-01 10:00:00+00:00: INFO:Entering state \"StartDatabridgeStreamer\"",
            "2024-04-01 10:00:01+00:00: INFO:Modem Statistics for modem 3: 500kbps, 2% loss, 40ms delay",
            "2024-04-01 10:00:02+00:00: INFO:Modem removed id: 3",
            "2024-04-01 10:00:03+00:00: INFO:Modem Statistics for modem 3: 450kbps, 3% loss, 42ms delay",
            "2024-04-01 10:00:04+00:00: INFO:Entering state \"StopCollectorAndStreamer\"",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = DataBridgeBandwidthParser('md-db-bw')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertEqual(parsed['mode'], 'md-db-bw')
            self.assertIn('3', parsed['modems'])
            self.assertEqual(parsed['modems']['3'][0]['notes'], '')
            self.assertEqual(parsed['modems']['3'][1]['notes'], 'Modem disconnected')
            self.assertTrue(any(event['notes'] == 'Stream start' for event in parsed['events']))
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
