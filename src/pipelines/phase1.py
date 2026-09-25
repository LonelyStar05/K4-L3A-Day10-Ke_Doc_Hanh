from __future__ import annotations

from core.config import load_settings
from core.utils import write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Run the reproducible baseline pipeline end to end."""
    settings = load_settings()
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    clean_df = build_clean_dataframe(records, settings.run_date)
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = quality["freshness"]
    write_json(settings.paths.freshness_report, freshness)
    if not quality["success"]:
        raise RuntimeError("Baseline data failed the quality gate; inspect the quality report.")

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    test_set = load_or_create_test_set(
        clean_df,
        settings.paths.test_set_json,
        refresh=settings.refresh_test_set,
    )
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.test_set_json,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    demo_answers = [
        answer_question(sample["question"], settings, index).__dict__
        for sample in test_set.samples[:3]
    ]
    write_json(settings.paths.demo_answers, demo_answers)
    generate_phase1_report(
        settings.paths.baseline_report,
        {
            "source": settings.source_api,
            "records": len(records),
            "clean_records": len(clean_df),
            "collection": settings.baseline_collection_name,
        },
        evaluation.summary,
        quality,
        freshness,
    )
    print(f"Baseline complete: {len(clean_df)} clean rows")
    print(f"Retrieval hit rate: {evaluation.summary['retrieval_hit_rate']:.3f}")
    print(f"Report: {settings.paths.baseline_report}")
