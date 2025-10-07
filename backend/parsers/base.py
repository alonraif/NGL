"""Shared parser base classes and utilities."""
from __future__ import annotations

import shutil
import tempfile
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .utils.archive_reader import ArchiveReader, LogLine


class CancellationException(Exception):
    """Raised when a running parser is cancelled."""


class DateRange:
    """Inclusive date range matcher mirroring lula2 behaviour."""

    def __init__(self, start=None, end=None):
        from dateutil.parser import parse
        from pytz import UTC

        self.start = None
        self.end = None

        if start:
            parsed = parse(start)
            if parsed.tzinfo is None:
                parsed = UTC.localize(parsed)
            self.start = parsed

        if end:
            parsed = parse(end)
            if parsed.tzinfo is None:
                parsed = UTC.localize(parsed)
            self.end = parsed

    def contains(self, dt) -> bool:
        if dt is None:
            return False
        from pytz import UTC

        check = dt
        if check.tzinfo is None:
            check = UTC.localize(check)

        if self.start and check < self.start:
            return False
        if self.end and check > self.end:
            return False
        return True


class BaseParser(ABC):
    """Base class for modular parsers."""

    def __init__(self, mode: str):
        self.mode = mode
        self.cancelled = threading.Event()

    def cancel(self) -> None:
        self.cancelled.set()

    def ensure_not_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise CancellationException("Parsing cancelled by user")

    def iter_archive(self, archive_path: str, *, timezone: str = "US/Eastern") -> Iterator[LogLine]:
        reader = ArchiveReader(archive_path, parse_mode=self.mode)
        yield from reader.iter_lines()

    @abstractmethod
    def parse(self, archive_path: str, *, timezone: str, begin_date: Optional[str], end_date: Optional[str]):
        raise NotImplementedError

    def process(self, archive_path: str, timezone: str = "US/Eastern", begin_date: Optional[str] = None, end_date: Optional[str] = None):
        return self.parse(archive_path, timezone=timezone, begin_date=begin_date, end_date=end_date)
