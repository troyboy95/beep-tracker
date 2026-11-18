"""Build source adapters from the curated `companies.toml`."""

import tomllib
from pathlib import Path

from beep.sources.adapters import ADAPTERS
from beep.sources.base import Source

COMPANIES_FILE = Path(__file__).with_name("companies.toml")


def load_sources(path: Path = COMPANIES_FILE, only: set[str] | None = None) -> list[Source]:
    with path.open("rb") as f:
        cfg = tomllib.load(f)
    sources: list[Source] = []
    for ats, boards in cfg.items():
        if ats not in ADAPTERS:
            raise ValueError(f"unknown ATS '{ats}' in {path.name}")
        if only and ats not in only:
            continue
        sources.extend(ADAPTERS[ats](board=b["token"], company=b["name"]) for b in boards)
    return sources
