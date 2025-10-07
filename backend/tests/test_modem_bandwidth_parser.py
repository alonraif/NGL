import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.bandwidth import ModemBandwidthParser


class ModemBandwidthParserTests(unittest.TestCase):
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

    def test_parses_modem_rows(self):
        lines = [
            "2024-04-01 10:00:00+00:00: INFO:Modem Statistics for modem 1: potentialBW 1000kbps, 2% loss, 30ms up extrapolated delay, 20ms shortest round trip delay, 25ms smooth round trip delay, 22ms minimum smooth round trip delay",
            "2024-04-01 10:00:05+00:00: INFO:Modem Statistics for modem 2: potentialBW 800kbps, 1% loss, 25ms up extrapolated delay, 18ms shortest round trip delay, 22ms smooth round trip delay, 19ms minimum smooth round trip delay",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = ModemBandwidthParser('md-bw')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertEqual(parsed['mode'], 'md-bw')
            self.assertEqual(len(parsed['modems']), 2)
            self.assertEqual(parsed['aggregated'][0]['total_bw'], 1800)
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
