"""Common post model and source adapter contract."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from beep.http import PoliteClient


@dataclass(slots=True)
class RawPost:
    """A job post mapped to a common shape (pre-normalization)."""

    source: str
    board: str  # ATS board token, e.g. "stripe"
    external_id: str
    url: str
    title: str
    company: str
    location_raw: str
    description: str  # HTML or plain text; normalized later
    posted_at: datetime | None = None
    hints: str = ""  # structured extras from the source (employment type, level), fed to the LLM


# Cheap title predicate applied before expensive per-post requests (e.g. SmartRecruiters detail).
TitleFilter = Callable[[str], bool]


class Source(Protocol):
    name: str
    board: str

    def fetch(self, http: PoliteClient, keep_title: TitleFilter) -> list[RawPost]: ...
