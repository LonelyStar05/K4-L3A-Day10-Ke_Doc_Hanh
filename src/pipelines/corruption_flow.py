from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.dashboard import build_dashboard
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import main as run_baseline
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corrupt, detect, auto-repair from raw lineage, and compare all states."""
    settings = load_settings()
    required = [settings.paths.clean_json, settings.paths.baseline_metrics, settings.paths.test_set_json]
    if not all(path.exists() for path in required):
        run_baseline()

    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        settings.paths.corrupted_embeddings_json,
    )
    corrupted_eval = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.test_set_json,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    # Self-healing always reconstructs from the immutable raw snapshot.
    repaired_df = build_clean_dataframe(
        load_raw_records(settings.paths.raw_records_json),
        datetime.now(UTC),
    )
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        settings.paths.repaired_embeddings_json,
    )
    repaired_eval = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.test_set_json,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_eval.summary,
        repaired_eval.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print("Metric                 Baseline  Corrupted  Repaired")
    for metric in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        print(
            f"{metric:22} {baseline_metrics[metric]:8.3f} "
            f"{corrupted_eval.summary[metric]:10.3f} {repaired_eval.summary[metric]:9.3f}"
        )
    print(f"Comparison report: {settings.paths.comparison_report}")
    print(f"Observability dashboard: {build_dashboard(settings)}")
