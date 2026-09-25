from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into the stable raw-record contract."""

    def clean_markup(value: str) -> str:
        without_tags = re.sub(r"<[^>]+>", " ", unescape(value or ""))
        return normalize_whitespace(without_tags)

    def parse_date(item: dict, *keys: str) -> str:
        for key in keys:
            value = item.get(key) or {}
            parts = value.get("date-parts") or []
            if parts and parts[0]:
                year, month, day = (list(parts[0]) + [1, 1])[:3]
                try:
                    return date(int(year), int(month), int(day)).isoformat()
                except (TypeError, ValueError):
                    continue
            date_time = value.get("date-time")
            if date_time:
                return str(date_time)[:10]
        return ""

    if not isinstance(payload, dict):
        return []
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = normalize_whitespace(str(item.get("DOI", ""))).lower()
        titles = item.get("title") or []
        title = clean_markup(str(titles[0])) if titles else ""
        summary = clean_markup(str(item.get("abstract", "")))
        if not paper_id or not title or not summary or paper_id in seen_ids:
            continue

        authors = []
        for author in item.get("author") or []:
            if not isinstance(author, dict):
                continue
            full_name = normalize_whitespace(
                " ".join(
                    part
                    for part in [str(author.get("given", "")), str(author.get("family", ""))]
                    if part
                )
            )
            if full_name:
                authors.append(full_name)

        categories = [
            normalize_whitespace(str(subject))
            for subject in (item.get("subject") or [])
            if normalize_whitespace(str(subject))
        ]
        published = parse_date(item, "published", "published-print", "published-online", "created")
        updated = parse_date(item, "updated-by", "created") or published
        resource_url = normalize_whitespace(str(item.get("URL", "")))
        links = item.get("link") or []
        pdf_url = next(
            (
                str(link.get("URL", ""))
                for link in links
                if isinstance(link, dict) and "pdf" in str(link.get("content-type", "")).lower()
            ),
            resource_url,
        )

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors or ["Unknown author"],
                categories=categories or ["Uncategorized"],
                primary_category=(categories or ["Uncategorized"])[0],
                published=published,
                updated=updated,
                abs_url=resource_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
        seen_ids.add(paper_id)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref with retry, then fall back to the bundled snapshot."""
    snapshot_path = settings.paths.raw_api_response
    payload: dict | None = None

    if not settings.refresh_source and snapshot_path.exists():
        payload = read_json(snapshot_path)
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        headers = {"User-Agent": "day10-data-observability-lab/1.0 (educational use)"}
        for attempt in range(4):
            try:
                response = requests.get(
                    "https://api.crossref.org/works",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"Transient Crossref status {response.status_code}")
                response.raise_for_status()
                payload = response.json()
                write_json(snapshot_path, payload)
                break
            except (requests.RequestException, ValueError):
                if attempt < 3:
                    time.sleep(2**attempt)

    if payload is None:
        if not snapshot_path.exists():
            raise RuntimeError("Crossref request failed and no local snapshot is available.")
        payload = read_json(snapshot_path)

    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref payload did not contain any usable paper records.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the normalized raw snapshot into typed records."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of raw records in {path}")
    records = [PaperRecord(**item) for item in payload]
    if not records:
        raise ValueError(f"No raw records found in {path}")
    return records
