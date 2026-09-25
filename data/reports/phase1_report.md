# Phase 1 Baseline Report

## Source and lineage

| Field | Value |
| --- | --- |
| Source | Crossref REST API |
| Raw records | 24 |
| Clean records | 24 |
| Collection | papers-baseline |

## Baseline evaluation

| Metric | Value |
| --- | ---: |
| Retrieval hit rate | 1.000 |
| Mean token F1 | 1.000 |
| Judge accuracy | 1.000 |
| Mean judge score | 5.000 |

## Data quality gate

Overall status: **PASS**

Validation engine: `great-expectations-1.x`

| Check | Status | Observed |
| --- | --- | --- |
| row_count_between_5_and_5000 | PASS | 24 |
| required_values_not_null | PASS | {'paper_id': 0, 'title': 0, 'text_for_embedding': 0} |
| paper_id_unique | PASS | 0 |
| summary_length_at_least_30 | PASS | 0 |

## Freshness SLA

| Signal | Value |
| --- | --- |
| Latest publication | 2026-07-22 |
| Oldest publication | 2026-03-28 |
| Stale rows | 1 / 24 |
| Stale ratio | 0.042 |
| Is fresh | True |
