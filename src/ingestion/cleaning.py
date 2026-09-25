from __future__ import annotations

from datetime import datetime
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    rows = []
    ref_date = run_date.date() if isinstance(run_date, datetime) else run_date

    for r in records:
        paper_id = str(r.paper_id).strip()
        title = normalize_whitespace(str(r.title))
        summary = normalize_whitespace(str(r.summary))

        authors = [normalize_whitespace(a) for a in r.authors if a.strip()]
        authors_joined = compact_join(authors, ", ")

        categories = [normalize_whitespace(c) for c in r.categories if c.strip()]
        categories_joined = compact_join(categories, ", ")
        primary_category = str(r.primary_category).strip() or (categories[0] if categories else "General")

        published = str(r.published).strip()
        updated = str(r.updated).strip() or published

        # Calculate age_days = (run_date - published).days
        try:
            pub_date = datetime.fromisoformat(published[:10]).date()
            age_days = (ref_date - pub_date).days
        except Exception:
            age_days = 0

        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append({
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "authors_joined": authors_joined,
            "categories": categories,
            "categories_joined": categories_joined,
            "primary_category": primary_category,
            "published": published,
            "updated": updated,
            "abs_url": str(r.abs_url).strip(),
            "pdf_url": str(r.pdf_url).strip(),
            "comment": str(r.comment).strip(),
            "age_days": age_days,
            "summary_chars": summary_chars,
            "text_for_embedding": text_for_embedding,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # 5. Drop duplicates on paper_id and filter bad rows
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["paper_id"].str.strip().ne("") & df["title"].str.strip().ne("")].copy()

    # 6. Sort dataframe and reset index
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
