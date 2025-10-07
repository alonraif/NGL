"""Utilities for reading log archives without relying on shell commands."""
from __future__ import annotations

import bz2
import gzip
import io
import os
import tarfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple


FFMPEG_MODES = {"ffmpeg", "ffmpegv", "ffmpega"}
DEFAULT_LOG_BASENAME = "messages.log"
FFMPEG_LOG_BASENAME = "ffmpeg_streamId__cdn_0__outputIndex__0.txt"


@dataclass(frozen=True)
class LogLine:
    """Represents a single log line emitted from an archive."""

    filename: str
    line: str


class ArchiveReader:
    """Read LiveU log archives using Python stdlib only.

    The reader understands both tar-based archives (``.tar``, ``.tar.gz``,
    ``.tar.bz2``) and single compressed files (``.gz`` / ``.bz2``) that are
    produced by LiveU systems.  For tar archives the iteration order matches
    the legacy ``lula2.py`` implementation: rotated log files are processed
    from highest index to lowest, followed by the active log file.
    """

    def __init__(self, archive_path: os.PathLike[str] | str, *, parse_mode: str = "known", encoding: str = "utf-8") -> None:
        self.archive_path = Path(archive_path)
        self.parse_mode = parse_mode
        self.encoding = encoding

    def iter_lines(self) -> Iterator[LogLine]:
        """Yield log lines from the archive in the same order as ``lula2``.

        The returned strings do not include newline characters, replicating the
        behaviour of ``splitlines()`` that the legacy script relied on.
        """

        if tarfile.is_tarfile(self.archive_path):
            yield from self._iter_tar_archive()
        else:
            yield from self._iter_single_file()

    # ------------------------------------------------------------------
    # Tar handling
    # ------------------------------------------------------------------
    def _iter_tar_archive(self) -> Iterator[LogLine]:
        with tarfile.open(self.archive_path, "r:*") as tar:
            members = self._select_members(tar)
            for member in members:
                if not member.isfile():
                    continue
                base_name = os.path.basename(member.name)
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                with closing(self._open_text_stream(extracted, base_name)) as stream:
                    for raw_line in stream:
                        yield LogLine(base_name, raw_line.rstrip("\n"))

    def _select_members(self, tar: tarfile.TarFile) -> List[tarfile.TarInfo]:
        root_name = self._log_basename()
        rotated: List[Tuple[int, tarfile.TarInfo]] = []
        current: List[tarfile.TarInfo] = []

        for member in tar.getmembers():
            if not member.isfile():
                continue
            base = os.path.basename(member.name)
            if base == root_name or base == f"{root_name}.gz" or base == f"{root_name}.bz2":
                current.append(member)
                continue
            if base.startswith(f"{root_name}."):
                index = self._rotation_index(base, root_name)
                if index is not None:
                    rotated.append((index, member))
                else:
                    # Unknown suffix, treat as current to maintain access.
                    current.append(member)

        rotated.sort(key=lambda item: item[0], reverse=True)
        ordered = [member for _, member in rotated]
        ordered.extend(current)
        return ordered

    # ------------------------------------------------------------------
    # Single file handling
    # ------------------------------------------------------------------
    def _iter_single_file(self) -> Iterator[LogLine]:
        base_name = self.archive_path.name
        with closing(self._open_path(self.archive_path)) as stream:
            for raw_line in stream:
                yield LogLine(base_name, raw_line.rstrip("\n"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log_basename(self) -> str:
        if self.parse_mode in FFMPEG_MODES:
            return FFMPEG_LOG_BASENAME
        return DEFAULT_LOG_BASENAME

    @staticmethod
    def _rotation_index(filename: str, base: str) -> Optional[int]:
        suffix = filename[len(base) + 1 :]
        # Strip any additional extension (e.g. ``.gz``)
        rotation_part = suffix.split(".")[0]
        try:
            return int(rotation_part)
        except ValueError:
            return None

    def _open_text_stream(self, fileobj, base_name: str) -> io.TextIOBase:
        if base_name.endswith(".gz"):
            gzip_file = gzip.GzipFile(fileobj=fileobj)
            return io.TextIOWrapper(gzip_file, encoding=self.encoding)
        if base_name.endswith(".bz2"):
            # ``bz2`` module does not accept a fileobj in the same way as gzip,
            # so we decompress eagerly and expose a ``StringIO`` view.
            data = fileobj.read()
            decompressed = bz2.decompress(data)
            return io.StringIO(decompressed.decode(self.encoding))
        return io.TextIOWrapper(fileobj, encoding=self.encoding)

    def _open_path(self, path: Path) -> io.TextIOBase:
        if path.suffix == ".gz":
            return io.TextIOWrapper(gzip.open(path, mode="rb"), encoding=self.encoding)
        if path.suffix == ".bz2":
            return io.TextIOWrapper(bz2.open(path, mode="rb"), encoding=self.encoding)
        return path.open("r", encoding=self.encoding)


__all__ = ["ArchiveReader", "LogLine"]
