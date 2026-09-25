# Báo cáo cá nhân - Nguyễn Phú Bình (02410)

## Vai trò

Data Foundation Owner.

## Phần việc

- Parse Crossref DOI, title, abstract JATS, authors, categories và publication date.
- Triển khai retry, xử lý 429 và fallback sang raw snapshot offline.
- Chuẩn hóa 24 records, tính `age_days`, deduplicate và tạo `text_for_embedding`.

## Bằng chứng

- `src/ingestion/crossref.py`
- `src/ingestion/cleaning.py`
- `data/raw/`
- `data/clean/papers_clean.csv`

## Kết quả học được

Hiểu cách bảo toàn raw lineage, thiết kế dual-mode ingestion và tạo data contract ổn định trước khi embedding.
