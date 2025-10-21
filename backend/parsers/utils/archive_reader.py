"""Utilities for reading log archives without relying on shell commands."""
from __future__ import annotations

import bz2
import gzip
import io
import logging
import os
import tarfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple


logger = logging.getLogger(__name__)

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

    def __init__(
        self,
        archive_path: os.PathLike[str] | str,
        *,
        parse_mode: str = "known",
        encoding: str = "utf-8",
        fallback_encodings: Optional[Sequence[str]] = None,
    ) -> None:
        self.archive_path = Path(archive_path)
        self.parse_mode = parse_mode
        self.encoding = encoding
        self._candidate_encodings = self._build_encoding_list(fallback_encodings)

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
                with closing(extracted):
                    data = self._read_member_bytes(extracted, base_name)
                yield from self._iter_lines_from_bytes(base_name, data)

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
        data = self._read_path_bytes(self.archive_path)
        yield from self._iter_lines_from_bytes(base_name, data)

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

    def _build_encoding_list(self, fallback_encodings: Optional[Sequence[str]]) -> List[str]:
        candidates = [self.encoding]
        fallbacks = fallback_encodings if fallback_encodings is not None else ("cp1252", "latin-1")
        for fallback in fallbacks:
            if fallback and fallback not in candidates:
                candidates.append(fallback)
        return candidates

    def _iter_lines_from_bytes(self, base_name: str, data: bytes) -> Iterator[LogLine]:
        text = self._decode_bytes(data, source=base_name)
        for line in text.splitlines():
            yield LogLine(base_name, line)

    def _decode_bytes(self, data: bytes, *, source: Optional[str] = None) -> str:
        last_exc: Optional[UnicodeDecodeError] = None
        for idx, encoding in enumerate(self._candidate_encodings):
            try:
                text = data.decode(encoding)
                if idx > 0 and source:
                    logger.warning(
                        "Decoded %s using fallback encoding %s (initial attempt with %s failed)",
                        source,
                        encoding,
                        self._candidate_encodings[0],
                    )
                return text
            except UnicodeDecodeError as exc:
                last_exc = exc
                continue
        if last_exc is not None:
            raise last_exc
        return data.decode(self.encoding)

    def _read_member_bytes(self, fileobj, base_name: str) -> bytes:
        raw = fileobj.read()
        if base_name.endswith(".gz"):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
                return gz.read()
        if base_name.endswith(".bz2"):
            return bz2.decompress(raw)
        return raw

    def _read_path_bytes(self, path: Path) -> bytes:
        if path.suffix == ".gz":
            with gzip.open(path, mode="rb") as gz:
                return gz.read()
        if path.suffix == ".bz2":
            with bz2.open(path, mode="rb") as bz_file:
                return bz_file.read()
        return path.read_bytes()


__all__ = ["ArchiveReader", "LogLine"]
