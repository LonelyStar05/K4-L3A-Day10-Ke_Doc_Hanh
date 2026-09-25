from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tao bo data quality checks bang Great Expectations 1.x va Freshness SLA.

    1. Check row count (5 den 5000).
    2. Check `paper_id`, `title`, `text_for_embedding` not null.
    3. Check `paper_id` unique.
    4. Check do dai `summary` toi thieu 30 ky tu.
    5. Check freshness bang `age_days` (ti le stale > 180 ngay khong vuot qua 25%).
    6. Ghi ket qua vao `data/quality/`.
    """
    total_rows = len(df)

    # 1. Great Expectations 1.x Ephemeral Setup
    context = gx.get_context(mode="ephemeral")
    source_name = f"papers_source_{report_name}"
    asset_name = f"papers_asset_{report_name}"
    batch_name = f"papers_batch_{report_name}"

    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 2. Add 4 essential expectations
    suite = gx.ExpectationSuite(name=f"papers_suite_{report_name}")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)
    gx_success = bool(validation_result.success)

    # 3. Freshness Check: stale if age_days > 180 (settings.freshness_threshold_days)
    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    elif "published" in df.columns:
        now_date = datetime.now(timezone.utc).date()
        stale_count = 0
        for p in df["published"]:
            try:
                pub_date = datetime.fromisoformat(str(p)[:10]).date()
                if (now_date - pub_date).days > settings.freshness_threshold_days:
                    stale_count += 1
            except Exception:
                pass
        stale_rows = stale_count
    else:
        stale_rows = 0

    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    overall_success = bool(gx_success and is_fresh)

    # 4. Determine report destination
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    # Also build freshness report
    freshness_summary = build_freshness_report(df, settings, settings.paths.freshness_report)

    report_payload: dict[str, Any] = {
        "report_name": report_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": is_fresh,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio_allowed": 0.25,
        "freshness_details": freshness_summary,
        "gx_results": validation_result.to_json_dict(),
    }

    write_json(report_path, report_payload)
    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str | None = None) -> dict[str, Any]:
    """Tong hop freshness report va luu JSON."""
    total_rows = len(df)
    latest_published = ""
    oldest_published = ""

    if total_rows > 0 and "published" in df.columns:
        published_series = pd.to_datetime(df["published"], errors="coerce")
        if not published_series.isna().all():
            latest_idx = published_series.argmax()
            oldest_idx = published_series.argmin()
            latest_published = str(df["published"].iloc[latest_idx])
            oldest_published = str(df["published"].iloc[oldest_idx])

    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    elif "published" in df.columns:
        now_date = datetime.now(timezone.utc).date()
        stale_count = 0
        for p in df["published"]:
            try:
                pub_date = datetime.fromisoformat(str(p)[:10]).date()
                if (now_date - pub_date).days > settings.freshness_threshold_days:
                    stale_count += 1
            except Exception:
                pass
        stale_rows = stale_count
    else:
        stale_rows = 0

    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
    }

    if report_path is not None:
        write_json(Path(report_path), payload)

    return payload
