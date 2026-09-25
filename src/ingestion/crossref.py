from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import re
import urllib.parse
import urllib.request

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)


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
    """Parse Crossref payload thanh list PaperRecord.

    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    if not isinstance(payload, dict):
        return []

    message = payload.get("message")
    if isinstance(message, dict):
        items = message.get("items", [])
    elif isinstance(payload.get("items"), list):
        items = payload.get("items", [])
    else:
        items = []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = str(item.get("DOI", "")).strip()

        titles = item.get("title", [])
        if isinstance(titles, list) and titles:
            title = normalize_whitespace(str(titles[0]))
        else:
            title = normalize_whitespace(str(item.get("title", "")))

        # summary: extract abstract, remove HTML/JATS XML tags, normalize whitespace
        raw_abstract = item.get("abstract", "") or item.get("summary", "")
        clean_summary = re.sub(r"<[^>]+>", "", str(raw_abstract))
        summary = normalize_whitespace(clean_summary)

        # authors: extract given + family
        authors: list[str] = []
        for author in item.get("author", []):
            if isinstance(author, dict):
                given = str(author.get("given", "")).strip()
                family = str(author.get("family", "")).strip()
                full_name = f"{given} {family}".strip() if (given or family) else str(author.get("name", "")).strip()
                if full_name:
                    authors.append(normalize_whitespace(full_name))
            elif isinstance(author, str) and author.strip():
                authors.append(normalize_whitespace(author))

        # categories & primary_category
        categories_raw = item.get("subject", []) or item.get("categories", [])
        if isinstance(categories_raw, list):
            categories = [normalize_whitespace(str(c)) for c in categories_raw if str(c).strip()]
        elif isinstance(categories_raw, str) and categories_raw.strip():
            categories = [normalize_whitespace(categories_raw)]
        else:
            categories = []
        primary_category = categories[0] if categories else "General"

        # published date
        published = ""
        pub_dict = item.get("published")
        if isinstance(pub_dict, dict):
            date_parts = pub_dict.get("date-parts", [[]])
            if date_parts and isinstance(date_parts[0], list):
                parts = date_parts[0]
                if len(parts) >= 3:
                    published = f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                elif len(parts) == 2:
                    published = f"{int(parts[0]):04d}-{int(parts[1]):02d}-01"
                elif len(parts) == 1:
                    published = f"{int(parts[0]):04d}-01-01"
        if not published and "created" in item and isinstance(item["created"], dict):
            created_dt = str(item["created"].get("date-time", ""))
            if len(created_dt) >= 10:
                published = created_dt[:10]
        if not published and isinstance(item.get("published"), str):
            published = str(item["published"]).strip()[:10]

        updated = published

        url = str(item.get("URL", "")).strip() or (f"https://doi.org/{doi}" if doi else "")
        abs_url = url
        pdf_url = url
        comment = f"Crossref record {doi}" if doi else "Crossref record"

        if not doi or not title:
            continue

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API hoac snapshot fallback, luu raw response, parse thanh records.

    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry/timeout; fallback snapshot neu loi hoac 429.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    payload: dict | None = None

    if settings.refresh_source:
        try:
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            query_str = urllib.parse.urlencode(params)
            api_url = f"https://api.crossref.org/works?{query_str}"
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "VinUni-RAG-Observability-Lab/1.0 (mailto:lab@vinuni.edu.vn)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    raw_data = resp.read().decode("utf-8")
                    payload = json.loads(raw_data)
                    write_json(settings.paths.raw_api_response, payload)
        except Exception as exc:
            logger.warning("Failed to fetch from live Crossref API (%s). Falling back to local snapshot.", exc)
            payload = None

    # Offline / Dual-mode fallback
    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        else:
            raise FileNotFoundError(
                f"Cannot find raw API response snapshot at {settings.paths.raw_api_response}."
            )

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=item.get("primary_category", "General"),
                published=item.get("published", ""),
                updated=item.get("updated", ""),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
        )
    return records
