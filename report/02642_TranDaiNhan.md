# Báo cáo cá nhân - Trần Đại Nhân (02642)

## Vai trò

Evaluation & Observability Owner.

## Phần việc

- Tạo benchmark năm loại câu hỏi dùng chung cho cả ba trạng thái dữ liệu.
- Xây GX 1.x quality gate và freshness SLA 180 ngày/25% stale ratio.
- Tổng hợp metrics và sinh báo cáo baseline/corruption có thể kiểm chứng.

## Bằng chứng

- `src/evaluation/testset.py`
- `src/observability/quality.py`
- `src/observability/reporting.py`
- `data/quality/`, `data/reports/`

## Kết quả học được

Hiểu cách tách data-quality signals khỏi model metrics và giữ benchmark cố định để so sánh công bằng.
