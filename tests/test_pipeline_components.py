from dataclasses import replace
from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.testset import load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records, parse_crossref_payload
from observability.quality import run_data_quality_checks


def _clean_dataframe():
    settings = load_settings()
    records = load_raw_records(settings.paths.raw_records_json)
    return settings, build_clean_dataframe(records, datetime.now(UTC))


def test_crossref_snapshot_parses_24_records():
    settings = load_settings()
    payload = read_json(settings.paths.raw_api_response)
    records = parse_crossref_payload(payload)

    assert len(records) == 24
    assert all(record.paper_id and record.title and record.published for record in records)
    assert all("<jats:" not in record.summary for record in records)


def test_clean_dataframe_has_stable_embedding_contract():
    _, df = _clean_dataframe()

    assert len(df) == 24
    assert df["paper_id"].is_unique
    assert df["summary_chars"].ge(30).all()
    assert df["text_for_embedding"].str.contains("Title:").all()
    assert df["text_for_embedding"].str.contains("Summary:").all()


def test_benchmark_has_five_required_question_types(tmp_path):
    settings, df = _clean_dataframe()
    test_set = load_or_create_test_set(df, tmp_path / "test_set.json", refresh=True)

    assert len(test_set.samples) == 5
    assert {sample["type"] for sample in test_set.samples} == {
        "summary",
        "authors",
        "date",
        "category",
        "multi_hop",
    }
    assert all(sample["ground_truth_doc_ids"] for sample in test_set.samples)


def test_corruption_injects_six_scenarios_and_keeps_row_count(tmp_path):
    _, df = _clean_dataframe()
    log_path = tmp_path / "corruption_log.json"
    corrupted = corrupt_clean_dataframe(df, log_path)
    log = read_json(log_path)

    assert len(corrupted) == 24
    assert log["scenario_count"] == 6
    assert corrupted["paper_id"].duplicated().any()
    assert corrupted["summary"].eq("").any()
    assert pd.to_numeric(corrupted["age_days"]).gt(180).mean() > 0.25


def test_quality_gate_accepts_clean_and_rejects_corrupted(tmp_path):
    settings, df = _clean_dataframe()
    paths = replace(settings.paths, quality_dir=tmp_path)
    test_settings = replace(settings, paths=paths)

    clean_result = run_data_quality_checks(df, test_settings, "unit-clean")
    corrupted = corrupt_clean_dataframe(df, tmp_path / "corruption_log.json")
    corrupted_result = run_data_quality_checks(corrupted, test_settings, "unit-corrupted")

    assert clean_result["success"] is True
    assert corrupted_result["success"] is False
