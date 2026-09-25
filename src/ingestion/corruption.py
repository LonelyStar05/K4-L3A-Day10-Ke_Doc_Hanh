from __future__ import annotations

from math import ceil

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six deterministic failure modes and record their lineage."""
    if len(df) < 10:
        raise ValueError("At least 10 clean rows are required for the corruption exercise.")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    events: list[dict] = []

    latest_count = max(1, ceil(len(corrupted) * 0.2))
    latest_indices = corrupted.sort_values("published", ascending=False).head(latest_count).index.tolist()
    dropped_ids = corrupted.loc[latest_indices, "paper_id"].tolist()
    corrupted = corrupted.drop(index=latest_indices).reset_index(drop=True)
    events.append({"type": "drop_latest_records", "count": len(dropped_ids), "paper_ids": dropped_ids})

    blank_indices = list(range(min(3, len(corrupted))))
    blank_ids = corrupted.loc[blank_indices, "paper_id"].tolist()
    corrupted.loc[blank_indices, "summary"] = ""
    corrupted.loc[blank_indices, "summary_chars"] = 0
    events.append({"type": "blank_summary", "count": len(blank_ids), "paper_ids": blank_ids})

    noise_indices = list(range(3, min(6, len(corrupted))))
    noise_ids = corrupted.loc[noise_indices, "paper_id"].tolist()
    corrupted.loc[noise_indices, "summary"] = corrupted.loc[noise_indices, "summary"].map(
        lambda value: f"### CORRUPTED @@ 0000 ## {value}"
    )
    corrupted.loc[noise_indices, "summary_chars"] = corrupted.loc[noise_indices, "summary"].str.len()
    events.append({"type": "inject_noise", "count": len(noise_ids), "paper_ids": noise_ids})

    title_indices = list(range(6, min(9, len(corrupted))))
    title_ids = corrupted.loc[title_indices, "paper_id"].tolist()
    corrupted.loc[title_indices, "title"] = corrupted.loc[title_indices, "title"].map(lambda value: value[:7])
    events.append({"type": "truncate_title", "count": len(title_ids), "paper_ids": title_ids})

    stale_count = max(1, ceil(len(corrupted) * 0.4))
    stale_indices = corrupted.sort_values("published", ascending=False).head(stale_count).index.tolist()
    stale_ids = corrupted.loc[stale_indices, "paper_id"].tolist()
    days_shifted = 365 * 5
    published = pd.to_datetime(corrupted.loc[stale_indices, "published"], errors="coerce") - pd.Timedelta(days=days_shifted)
    corrupted.loc[stale_indices, "published"] = published.dt.strftime("%Y-%m-%d").values
    corrupted.loc[stale_indices, "age_days"] = corrupted.loc[stale_indices, "age_days"].astype(int) + days_shifted
    events.append({"type": "stale_date", "count": len(stale_ids), "paper_ids": stale_ids, "days_shifted": days_shifted})

    # Replace the dropped rows with duplicates so the corruption flow keeps 24 rows.
    duplicate_rows = corrupted.head(latest_count).copy()
    duplicate_ids = duplicate_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    events.append({"type": "duplicate_rows", "count": len(duplicate_ids), "paper_ids": duplicate_ids})

    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: "\n".join(
            [
                f"Title: {row['title']}",
                f"Authors: {row['authors_joined']}",
                f"Published: {row['published']}",
                f"Categories: {row['categories_joined']}",
                f"Summary: {row['summary']}",
            ]
        ),
        axis=1,
    )
    write_json(
        output_log_path,
        {
            "input_rows": len(df),
            "output_rows": len(corrupted),
            "scenario_count": len(events),
            "events": events,
        },
    )
    return corrupted.reset_index(drop=True)
