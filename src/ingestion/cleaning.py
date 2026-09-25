from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records and build the pre-embedding data model."""

    def clean_text(value: str) -> str:
        return normalize_whitespace(re.sub(r"<[^>]+>", " ", unescape(value or "")))

    rows = []
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")

    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = clean_text(record.title)
        summary = clean_text(record.summary)
        authors = [clean_text(author) for author in record.authors if clean_text(author)]
        categories = [clean_text(category) for category in record.categories if clean_text(category)]
        published_ts = pd.to_datetime(record.published, utc=True, errors="coerce")
        updated_ts = pd.to_datetime(record.updated or record.published, utc=True, errors="coerce")
        if not paper_id or not title or len(summary) < 30 or pd.isna(published_ts):
            continue

        published = published_ts.date().isoformat()
        updated = (updated_ts if not pd.isna(updated_ts) else published_ts).date().isoformat()
        authors_joined = ", ".join(authors) or "Unknown author"
        categories_joined = ", ".join(categories) or "Uncategorized"
        age_days = max(0, int((run_timestamp.normalize() - published_ts.normalize()).days))
        text_for_embedding = "\n".join(
            [
                f"Title: {title}",
                f"Authors: {authors_joined}",
                f"Published: {published}",
                f"Categories: {categories_joined}",
                f"Summary: {summary}",
            ]
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": clean_text(record.primary_category) or categories_joined.split(", ")[0],
                "published": published,
                "updated": updated,
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    columns = [
        "paper_id",
        "title",
        "summary",
        "authors",
        "categories",
        "primary_category",
        "published",
        "updated",
        "abs_url",
        "pdf_url",
        "comment",
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "age_days",
        "text_for_embedding",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        raise ValueError("Cleaning removed every raw record; inspect the source snapshot.")
    return (
        df.drop_duplicates(subset=["paper_id"], keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
