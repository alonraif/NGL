import gzip
import tarfile
import tempfile
import unittest
from pathlib import Path

from backend.parsers.utils.archive_reader import ArchiveReader, LogLine


class ArchiveReaderTests(unittest.TestCase):
    def test_iter_lines_tar_with_rotations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create sample log files
            (tmp_path / "messages.log").write_text("current-1\ncurrent-2\n", encoding="utf-8")
            (tmp_path / "messages.log.1").write_text("rot1-1\n", encoding="utf-8")
            with gzip.open(tmp_path / "messages.log.2.gz", "wt", encoding="utf-8") as gz:
                gz.write("rot2-1\nrot2-2\n")

            archive_path = tmp_path / "logs.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                for name in ["messages.log.2.gz", "messages.log.1", "messages.log"]:
                    tar.add(tmp_path / name, arcname=name)

            reader = ArchiveReader(archive_path, parse_mode="known")
            lines = list(reader.iter_lines())

            expected = [
                LogLine("messages.log.2.gz", "rot2-1"),
                LogLine("messages.log.2.gz", "rot2-2"),
                LogLine("messages.log.1", "rot1-1"),
                LogLine("messages.log", "current-1"),
                LogLine("messages.log", "current-2"),
            ]
            self.assertEqual(lines, expected)

    def test_iter_lines_tar_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ffmpeg_name = "ffmpeg_streamId__cdn_0__outputIndex__0.txt"
            (tmp_path / ffmpeg_name).write_text("ffmpeg-line\n", encoding="utf-8")
            (tmp_path / "messages.log").write_text("should-not-appear\n", encoding="utf-8")

            archive_path = tmp_path / "ffmpeg.tar"
            with tarfile.open(archive_path, "w") as tar:
                tar.add(tmp_path / ffmpeg_name, arcname=ffmpeg_name)
                tar.add(tmp_path / "messages.log", arcname="messages.log")

            reader = ArchiveReader(archive_path, parse_mode="ffmpeg")
            lines = list(reader.iter_lines())

            expected = [LogLine(ffmpeg_name, "ffmpeg-line")]
            self.assertEqual(lines, expected)

    def test_iter_lines_single_gz_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            gz_path = tmp_path / "messages.log.gz"
            with gzip.open(gz_path, "wt", encoding="utf-8") as gz:
                gz.write("single-1\nsingle-2\n")

            reader = ArchiveReader(gz_path, parse_mode="known")
            lines = list(reader.iter_lines())

            expected = [
                LogLine("messages.log.gz", "single-1"),
                LogLine("messages.log.gz", "single-2"),
            ]
            self.assertEqual(lines, expected)

    def test_iter_lines_fallback_encoding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            log_path = tmp_path / "messages.log"
            log_path.write_bytes(b"alpha\nbeta\xacgamma\n")

            reader = ArchiveReader(log_path, parse_mode="known")
            lines = list(reader.iter_lines())

            expected = [
                LogLine("messages.log", "alpha"),
                LogLine("messages.log", f"beta{chr(0xAC)}gamma"),
            ]
            self.assertEqual(lines, expected)


if __name__ == "__main__":
    unittest.main()
