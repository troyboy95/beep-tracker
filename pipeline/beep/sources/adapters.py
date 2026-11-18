"""Adapters for public ATS job-board APIs. See SOURCES.md for endpoints and terms."""

import html
from dataclasses import dataclass
from datetime import UTC, datetime

from beep.http import PoliteClient
from beep.sources.base import RawPost, TitleFilter


def _iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _join(*parts: str | None) -> str:
    seen: list[str] = []
    for p in parts:
        if p and p.strip() and p.strip() not in seen:
            seen.append(p.strip())
    return " | ".join(seen)


@dataclass
class Greenhouse:
    board: str
    company: str
    name: str = "greenhouse"

    def fetch(self, http: PoliteClient, keep_title: TitleFilter) -> list[RawPost]:
        data = http.get_json(
            f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs",
            params={"content": "true"},
        )
        out = []
        for j in data.get("jobs", []):
            if not keep_title(j.get("title", "")):
                continue
            out.append(
                RawPost(
                    source=self.name,
                    board=self.board,
                    external_id=str(j["id"]),
                    url=j["absolute_url"],
                    title=j["title"],
                    company=self.company,
                    location_raw=(j.get("location") or {}).get("name") or "",
                    # Greenhouse returns HTML-escaped HTML.
                    description=html.unescape(j.get("content") or ""),
                    posted_at=_iso(j.get("first_published") or j.get("updated_at")),
                )
            )
        return out


@dataclass
class Lever:
    board: str
    company: str
    name: str = "lever"

    def fetch(self, http: PoliteClient, keep_title: TitleFilter) -> list[RawPost]:
        data = http.get_json(
            f"https://api.lever.co/v0/postings/{self.board}", params={"mode": "json"}
        )
        out = []
        for j in data:
            if not keep_title(j.get("text", "")):
                continue
            cat = j.get("categories") or {}
            locs = cat.get("allLocations") or [cat.get("location")]
            country = "India" if j.get("country") == "IN" else j.get("country")
            lists = " ".join(
                f"<h3>{x.get('text', '')}</h3>{x.get('content', '')}" for x in j.get("lists") or []
            )
            created = j.get("createdAt")
            out.append(
                RawPost(
                    source=self.name,
                    board=self.board,
                    external_id=j["id"],
                    url=j["hostedUrl"],
                    title=j["text"],
                    company=self.company,
                    location_raw=_join(*locs, country),
                    description=f"{j.get('description', '')} {lists} {j.get('additional', '')}",
                    posted_at=datetime.fromtimestamp(created / 1000, UTC) if created else None,
                    hints=_join(cat.get("commitment"), j.get("workplaceType")),
                )
            )
        return out


@dataclass
class Ashby:
    board: str
    company: str
    name: str = "ashby"

    def fetch(self, http: PoliteClient, keep_title: TitleFilter) -> list[RawPost]:
        data = http.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{self.board}")
        out = []
        for j in data.get("jobs", []):
            if j.get("isListed") is False or not keep_title(j.get("title", "")):
                continue
            country = (((j.get("address") or {}).get("postalAddress")) or {}).get(
                "addressCountry"
            )
            secondary = [s.get("location") for s in j.get("secondaryLocations") or []]
            out.append(
                RawPost(
                    source=self.name,
                    board=self.board,
                    external_id=j["id"],
                    url=j["jobUrl"],
                    title=j["title"],
                    company=self.company,
                    location_raw=_join(j.get("location"), *secondary, country),
                    description=j.get("descriptionHtml") or j.get("descriptionPlain") or "",
                    posted_at=_iso(j.get("publishedAt")),
                    hints=_join(j.get("employmentType"), j.get("workplaceType")),
                )
            )
        return out


@dataclass
class SmartRecruiters:
    board: str
    company: str
    name: str = "smartrecruiters"
    max_posts: int = 3000

    def fetch(self, http: PoliteClient, keep_title: TitleFilter) -> list[RawPost]:
        base = f"https://api.smartrecruiters.com/v1/companies/{self.board}/postings"
        listing, offset = [], 0
        while offset < self.max_posts:
            page = http.get_json(base, params={"country": "in", "limit": 100, "offset": offset})
            content = page.get("content", [])
            listing.extend(content)
            offset += len(content)
            if not content or offset >= page.get("totalFound", 0):
                break

        out = []
        for j in listing:
            if not keep_title(j.get("name", "")):
                continue  # skip the per-post detail request for obviously senior roles
            d = http.get_json(f"{base}/{j['id']}")
            sections = (d.get("jobAd") or {}).get("sections") or {}
            desc = " ".join(
                f"<h3>{s.get('title', '')}</h3>{s.get('text', '')}"
                for k, s in sections.items()
                if k != "companyDescription" and s
            )
            loc = j.get("location") or {}
            out.append(
                RawPost(
                    source=self.name,
                    board=self.board,
                    external_id=str(j["id"]),
                    url=d.get("postingUrl")
                    or f"https://jobs.smartrecruiters.com/{self.board}/{j['id']}",
                    title=j["name"],
                    company=self.company,
                    location_raw=_join(
                        loc.get("city"), loc.get("region"), "Remote" if loc.get("remote") else None,
                        "India",
                    ),
                    description=desc,
                    posted_at=_iso(j.get("releasedDate")),
                    hints=_join(
                        (j.get("typeOfEmployment") or {}).get("label"),
                        "experience level: " + (j.get("experienceLevel") or {}).get("label", "")
                        if j.get("experienceLevel")
                        else None,
                    ),
                )
            )
        return out


ADAPTERS = {
    "greenhouse": Greenhouse,
    "lever": Lever,
    "ashby": Ashby,
    "smartrecruiters": SmartRecruiters,
}
