import tarfile
import tempfile
from pathlib import Path
import unittest

from backend.parsers.modem_events import ModemEventsParser, ModemEventsSortedParser


class ModemEventsParserTests(unittest.TestCase):
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

    def test_modem_events(self):
        lines = [
            "2024-04-01 10:00:00+00:00: INFO: USB port 1: Current operator: Vodafone, technology: 4G (",
            "2024-04-01 10:00:05+00:00: INFO: USB port 1: Link is ready for streaming: ({'description': 'T-Mobile', 'modemType': 'MC7455', 'iccid': '8985231234567890', 'technology': '4G', 'operatorName': 'T-Mobile', 'activeSim': 'A', 'isCurrentlyRoaming': True, 'rssi': -86}) (eaglenest/devices.py:180)",
            "2024-04-01 10:00:10+00:00: INFO: USB port 1: Link connected. APN: fast.m2m",
            "2024-04-01 10:00:15+00:00: streamer/video/modemupdater.py:73 INFO:found 6 links ready for streaming",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = ModemEventsParser('modemevents')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertEqual(len(parsed), 4)
            self.assertEqual(parsed[0]['event_type'], 'current_operator')
            self.assertEqual(parsed[1]['metadata']['provider'], 'Webbing')
            self.assertEqual(parsed[-1]['metadata']['count'], 6)
        finally:
            temp_dir.cleanup()

    def test_modem_events_sorted(self):
        lines = [
            "2024-04-01 10:00:00+00:00: INFO: USB port 2: DHCP link: <Link name: wlan0, local address: 192.168.0.2, gateway: 192.168.0.1, dns servers: ['192.168.0.1'], netmask: 255.255.255.0>",
            "2024-04-01 10:00:05+00:00: INFO: USB port 2: QMI link: <Link name: wwan11, local address: 10.7.85.42> is ready after: 2 attempts",
        ]
        temp_dir, archive_path = self._create_archive(lines)
        try:
            parser = ModemEventsSortedParser('modemeventssorted')
            result = parser.process(str(archive_path), timezone='UTC')
            parsed = result['parsed_data']

            self.assertIn('modems', parsed)
            self.assertEqual(len(parsed['modems']), 1)
            modem_events = parsed['modems'][0]['events']
            self.assertEqual(modem_events[0]['event_type'], 'dhcp_link')
            self.assertEqual(modem_events[1]['metadata']['attempts'], 2)
        finally:
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
