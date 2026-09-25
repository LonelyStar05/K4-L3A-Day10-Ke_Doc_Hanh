from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate the dataframe with GX 1.x and the freshness SLA."""
    required_columns = {"paper_id", "title", "summary", "text_for_embedding", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        payload = {
            "success": False,
            "engine": "schema-precheck",
            "row_count": len(df),
            "missing_columns": missing_columns,
            "checks": [],
        }
        write_json(settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json", payload)
        return payload

    checks = [
        {
            "name": "row_count_between_5_and_5000",
            "success": 5 <= len(df) <= 5000,
            "observed_value": len(df),
        },
        {
            "name": "required_values_not_null",
            "success": all(
                df[column].notna().all() and df[column].astype(str).str.strip().ne("").all()
                for column in ["paper_id", "title", "text_for_embedding"]
            ),
            "observed_value": {
                column: int((df[column].isna() | df[column].astype(str).str.strip().eq("")).sum())
                for column in ["paper_id", "title", "text_for_embedding"]
            },
        },
        {
            "name": "paper_id_unique",
            "success": bool(df["paper_id"].is_unique),
            "observed_value": int(df["paper_id"].duplicated(keep=False).sum()),
        },
        {
            "name": "summary_length_at_least_30",
            "success": bool(df["summary"].fillna("").astype(str).str.len().ge(30).all()),
            "observed_value": int(df["summary"].fillna("").astype(str).str.len().lt(30).sum()),
        },
    ]

    engine = "great-expectations-1.x"
    gx_success = False
    gx_results: dict[str, Any] | list[dict[str, Any]]
    try:
        import great_expectations as gx
        import great_expectations.expectations as gxe

        context = gx.get_context(mode="ephemeral")
        suffix = safe_slug(report_name)
        data_source = context.data_sources.add_pandas(name=f"papers_source_{suffix}")
        data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{suffix}")
        batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{suffix}")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})
        suite = gx.ExpectationSuite(name=f"papers_suite_{suffix}")
        suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
        for column in ["paper_id", "title", "text_for_embedding"]:
            suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=column))
        suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
        suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))
        validation_result = batch.validate(suite)
        gx_success = bool(validation_result.success)
        gx_results = validation_result.to_json_dict()
    except Exception as exc:
        engine = "manual-fallback"
        gx_success = all(check["success"] for check in checks)
        gx_results = [{"success": False, "error": f"GX validation unavailable: {exc}"}]

    freshness = build_freshness_report(
        df,
        settings,
        settings.paths.quality_dir / f"{safe_slug(report_name)}_freshness_report.json",
    )
    payload = {
        "report_name": report_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "success": bool(gx_success and freshness["is_fresh"] and all(check["success"] for check in checks)),
        "engine": engine,
        "gx_success": gx_success,
        "row_count": len(df),
        "checks": checks,
        "freshness": freshness,
        "gx_results": gx_results,
    }
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json"
    write_json(report_path, payload)
    return payload


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Measure the 180-day freshness SLA and persist the result."""
    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    age_days = pd.to_numeric(df["age_days"], errors="coerce")
    stale_rows = int(age_days.gt(settings.freshness_threshold_days).sum())
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "latest_published": published.max().date().isoformat() if published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "max_allowed_stale_ratio": 0.25,
        "is_fresh": bool(total_rows and stale_ratio <= 0.25),
    }
    if report_path is not None:
        write_json(Path(report_path), payload)
    return payload
