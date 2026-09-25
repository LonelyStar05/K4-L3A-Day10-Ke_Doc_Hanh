# Corruption and Idempotent Repair Report

## Three-state comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.000 | 0.000 | 1.000 |
| `mean_token_f1` | 1.000 | 0.321 | 1.000 |
| `judge_accuracy` | 1.000 | 0.400 | 1.000 |
| `mean_judge_score` | 5.000 | 2.200 | 5.000 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | N/A | FAIL | PASS |

## Findings

- The corrupted dataset triggers the uniqueness, summary-completeness, and freshness signals recorded in `data/quality/`.
- The same fixed benchmark is reused for all three states, so metric changes come from data/index changes rather than test-set drift.
- Repair is idempotent: it rebuilds the clean model from `data/raw/crossref_records.json`, then recreates the repaired Chroma collection.
- Repaired quality and evaluation should return to the baseline values; any remaining difference is visible in the table instead of being hidden.
