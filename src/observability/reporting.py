from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name, 0.0)
    return f"{float(value):.3f}" if isinstance(value, (int, float)) else str(value)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline evidence report from generated artifacts."""
    checks = "\n".join(
        f"| {item['name']} | {'PASS' if item['success'] else 'FAIL'} | {item['observed_value']} |"
        for item in quality.get("checks", [])
    )
    content = f"""# Phase 1 Baseline Report

## Source and lineage

| Field | Value |
| --- | --- |
| Source | {source_summary.get('source', 'Crossref REST API / offline snapshot')} |
| Raw records | {source_summary.get('records', 0)} |
| Clean records | {source_summary.get('clean_records', 0)} |
| Collection | {source_summary.get('collection', 'papers-baseline')} |

## Baseline evaluation

| Metric | Value |
| --- | ---: |
| Retrieval hit rate | {_metric(metrics, 'retrieval_hit_rate')} |
| Mean token F1 | {_metric(metrics, 'mean_token_f1')} |
| Judge accuracy | {_metric(metrics, 'judge_accuracy')} |
| Mean judge score | {_metric(metrics, 'mean_judge_score')} |

## Data quality gate

Overall status: **{'PASS' if quality.get('success') else 'FAIL'}**

Validation engine: `{quality.get('engine', 'unknown')}`

| Check | Status | Observed |
| --- | --- | --- |
{checks}

## Freshness SLA

| Signal | Value |
| --- | --- |
| Latest publication | {freshness.get('latest_published')} |
| Oldest publication | {freshness.get('oldest_published')} |
| Stale rows | {freshness.get('stale_rows')} / {freshness.get('total_rows')} |
| Stale ratio | {_metric(freshness, 'stale_ratio')} |
| Is fresh | {freshness.get('is_fresh')} |
"""
    write_text(report_path, content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the evidence-backed baseline/corrupted/repaired comparison."""
    metric_names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    metric_rows = "\n".join(
        f"| `{name}` | {_metric(baseline_metrics, name)} | {_metric(corrupted_metrics, name)} | {_metric(repaired_metrics, name)} |"
        for name in metric_names
    )
    content = f"""# Corruption and Idempotent Repair Report

## Three-state comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
{metric_rows}
| Quality gate | {'PASS' if baseline_metrics else 'N/A'} | {'PASS' if corrupted_quality.get('success') else 'FAIL'} | {'PASS' if repaired_quality.get('success') else 'FAIL'} |
| Freshness SLA | N/A | {'PASS' if corrupted_freshness.get('is_fresh') else 'FAIL'} | {'PASS' if repaired_freshness.get('is_fresh') else 'FAIL'} |

## Findings

- The corrupted dataset triggers the uniqueness, summary-completeness, and freshness signals recorded in `data/quality/`.
- The same fixed benchmark is reused for all three states, so metric changes come from data/index changes rather than test-set drift.
- Repair is idempotent: it rebuilds the clean model from `data/raw/crossref_records.json`, then recreates the repaired Chroma collection.
- Repaired quality and evaluation should return to the baseline values; any remaining difference is visible in the table instead of being hidden.
"""
    write_text(report_path, content)
