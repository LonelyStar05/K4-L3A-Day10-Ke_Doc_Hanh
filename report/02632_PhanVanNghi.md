# Báo cáo cá nhân - Phan Văn Nghị (02632)

## Vai trò

Observability & Evaluation Lead.

## Phần việc

- Xây GX 1.x quality gate và freshness SLA 180 ngày/25% stale ratio.
- Tạo benchmark năm loại câu hỏi dùng chung cho cả ba trạng thái dữ liệu.
- Tổng hợp metrics, đối chiếu artifacts và sinh báo cáo baseline/corruption có thể kiểm chứng.

## Bằng chứng

- `src/observability/quality.py`
- `src/observability/reporting.py`
- `src/evaluation/testset.py`
- `data/quality/`, `data/eval/`, `data/reports/`

## Kết quả học được

Hiểu cách tách data-quality signals khỏi model metrics và giữ benchmark cố định để so sánh công bằng.
