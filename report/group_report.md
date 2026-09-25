# Group Report - Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | Kẻ Độc Hành |
| Repository | https://github.com/LonelyStar05/K4-L3A-Day10-Ke_Doc_Hanh |
| Ngày hoàn thành | 2026-09-25 |

| STT | Họ và tên | MSSV | Vai trò chính |
| --: | --- | --- | --- |
| 1 | Nguyễn Tú Tài | 02455 | Pipeline Lead |
| 2 | Nguyễn Phú Bình | 02410 | Data Foundation Owner |
| 3 | Trần Đại Nhân | 02642 | RAG Specialist |
| 4 | Phan Văn Nghị | 02632 | Observability & Evaluation Lead |

## 2. Tóm tắt kết quả

Nhóm hoàn thiện pipeline Crossref dual-mode, giữ raw snapshot và chuẩn hóa 24 bài báo thành data model dùng cho embedding. Great Expectations 1.x kiểm tra row count, completeness, uniqueness, summary length; freshness SLA cảnh báo khi hơn 25% dữ liệu cũ quá 180 ngày. ChromaDB sử dụng `sentence-transformers/all-MiniLM-L6-v2`, benchmark cố định gồm năm loại câu hỏi. Baseline đạt retrieval hit rate và token F1 bằng 1.0. Sáu corruption scenarios làm retrieval hit rate giảm xuống 0.0 và token F1 còn 0.321. Self-healing tái tạo dữ liệu từ raw snapshot, rebuild collection riêng và phục hồi cả hai chỉ số về 1.0. Toàn bộ kết quả được lưu trong `data/results/`, `data/quality/` và `data/reports/`.

## 3. Kiến trúc

```text
Crossref API / offline snapshot
  -> typed raw records
  -> cleaning + data contract
  -> GX quality gate + freshness
  -> MiniLM embeddings + ChromaDB
  -> fixed benchmark + QA evaluation
  -> six corruption scenarios
  -> auto-repair from raw lineage
  -> three-state comparison report
```

## 4. Cách tái hiện

```bash
python -m pip install -e .
python script/run_phase1.py
python script/run_corruption_flow.py
python -m pytest -q
```

Khi không cấu hình API key, đặt `LLM_PROVIDER=mock`; pipeline retrieval và heuristic judge vẫn chạy offline, không ảnh hưởng phép so sánh ba trạng thái.

## 5. Data contract và quality

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Rows | 24 | 24 | 24 |
| Unique `paper_id` | Pass | Fail | Pass |
| Summary length >= 30 | Pass | Fail | Pass |
| Freshness stale ratio <= 25% | Pass | Fail | Pass |
| GX overall | Pass | Fail | Pass |

`text_for_embedding` luôn gồm Title, Authors, Published, Categories và Summary. Raw snapshot không bị sửa trong corruption flow.

## 6. Benchmark và metrics

Test set gồm `summary`, `authors`, `date`, `category`, `multi_hop` và được giữ nguyên cho cả ba lần đánh giá.

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.000 | 0.000 | 1.000 |
| Mean token F1 | 1.000 | 0.321 | 1.000 |
| Judge accuracy | 1.000 | 0.400 | 1.000 |
| Mean judge score | 5.000 | 2.200 | 5.000 |

## 7. Corruption và repair

| Scenario | Mô phỏng | Signal bị tác động |
| --- | --- | --- |
| Drop latest | Mất dữ liệu mới | Retrieval, freshness |
| Blank summary | Thiếu nội dung | Summary length, answer quality |
| Inject noise | Văn bản nhiễu | Embedding/retrieval |
| Truncate title | Metadata hỏng | Exact lookup/retrieval |
| Stale date | Lùi ngày 5 năm | Freshness SLA |
| Duplicate rows | Trùng dữ liệu | Unique key |

Repair không che lỗi tại output. Pipeline đọc lại `data/raw/crossref_records.json`, chạy cleaning, quality, embedding và evaluation từ đầu; vì vậy chạy lặp lại vẫn tạo cùng data model và metrics.

## 8. Giới hạn

- LLM judge mặc định có thể chạy heuristic khi chưa cung cấp API key; cần provider thật nếu muốn Ragas/LLM evaluation đầy đủ.
- Corpus lab chỉ có 24 records, phù hợp demo nhưng chưa đại diện production scale.
- Chroma binary index được tái tạo bằng script và không commit vào Git; embedding manifests và metrics được lưu để kiểm chứng cấu hình.

## 9. Checklist

- [x] Team information và phân công đã điền.
- [x] Baseline và corruption pipelines chạy end-to-end.
- [x] Test set dùng chung cho ba trạng thái.
- [x] Metrics khớp artifacts trong `data/results/`.
- [x] Quality/freshness reports đã sinh.
- [x] Có báo cáo cá nhân cho bốn thành viên.
- [x] Không commit `.env`, API key hoặc token.
