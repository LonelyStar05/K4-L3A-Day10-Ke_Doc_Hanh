# Báo cáo cá nhân - Nguyễn Phú Bình (02410)

## Vai trò

Corruption, Retrieval & Pipeline Integrator.

## Phần việc

- Xây ChromaDB index bằng MiniLM và semantic search.
- Tiêm sáu kịch bản corruption có log lineage chi tiết.
- Tích hợp baseline, corrupted và idempotent repair pipelines.

## Bằng chứng

- `src/retrieval/`
- `src/ingestion/corruption.py`
- `src/pipelines/`
- `data/results/`, `data/reports/corruption_report.md`

## Kết quả học được

Hiểu silent failure trong RAG và cách self-healing từ raw snapshot phục hồi đồng thời quality gate lẫn retrieval metrics.
