import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.bandwidth import StreamBandwidthParser


class StreamBandwidthParserTests(unittest.TestCase):
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

    def test_parses_bandwidth_rows(self):
        lines = [
            "2024-04-01 10:00:00+00:00: INFO: Detected flow in outgoing queue (available <Bandwidth: 400kbps>): Setting bitrate to <Bandwidth: 350kbps>",
            "2024-04-01 11:00:00+00:00: INFO: Detected congestion in outgoing queue:  drain time = 10 ms, potential bandwidth 320 kbps: Setting bitrate to 300 kbps",
            "2024-04-01 12:00:00+00:00: INFO: Entering state \"StartStreamer\" with args: ().'collectorAddressList': [[u'1.1.1.1', 1935]]",
            "2024-04-01 13:00:00+00:00: INFO: Entering state \"StopStreamer\"",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = StreamBandwidthParser('bw')
            result = parser.process(str(archive_path), timezone='UTC')

            parsed = result['parsed_data']
            self.assertGreater(len(parsed), 4)
            self.assertEqual(parsed[0]['datetime'], '2024-04-01 10:00:00')
            self.assertEqual(parsed[0]['total bitrate'], '400')
            self.assertEqual(parsed[0]['video bitrate'], '350')

            # Forward fill rows should be present between points
            self.assertTrue(any(entry['notes'] == '(forward filled)' for entry in parsed))

            self.assertEqual(parsed[-1]['notes'], 'Stream end')
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
