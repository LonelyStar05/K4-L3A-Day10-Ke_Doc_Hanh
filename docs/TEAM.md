# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Kẻ Độc Hành`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3A-Day10-Ke_Doc_Hanh`

---

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Tú Tài | 02455 | — | Data Ingestion & Cleaning Owner (`crossref.py`, `cleaning.py`, raw/clean artifacts) | `report/02455_NguyenTuTai.md` |
| 2 | Trần Đại Nhân | 02642 | — | Evaluation & Observability Owner (`testset.py`, `quality.py`, reporting) | `report/02642_TranDaiNhan.md` |
| 3 | Nguyễn Phú Bình | 02410 | — | Corruption, Retrieval & Pipeline Integrator (`corruption.py`, ChromaDB, phase pipelines) | `report/02410_NguyenPhuBinh.md` |

---

## Cá nhân

### Nguyễn Tú Tài - 02455

- **Vai trò:** Phụ trách nguồn dữ liệu, chuẩn hóa và data lineage.
- **Công việc chi tiết:**
  - Bóc tách Crossref payload, chuẩn hóa DOI, tiêu đề, JATS abstract, tác giả, chuyên ngành và ngày ISO 8601.
  - Hoàn thiện cơ chế retry và offline fallback từ `data/raw/crossref_response.json`.
  - Xây dựng clean dataframe 24 dòng, tính `age_days`, khử trùng lặp và tạo `text_for_embedding` năm phần.
- **Kết quả:** `data/raw/`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`.

### Trần Đại Nhân - 02642

- **Vai trò:** Phụ trách benchmark, data quality, freshness và báo cáo.
- **Công việc chi tiết:**
  - Xây dựng test set cố định gồm năm loại câu hỏi: summary, authors, date, category và multi-hop.
  - Thiết lập Great Expectations 1.x bằng ephemeral context, kiểm tra row count, null, unique và độ dài summary.
  - Theo dõi freshness SLA, tổng hợp baseline/corrupted/repaired metrics và báo cáo Markdown.
- **Kết quả:** `data/eval/test_set.json`, `data/quality/`, `data/reports/`.

### Nguyễn Phú Bình - 02410

- **Vai trò:** Phụ trách retrieval, corruption/repair và tích hợp pipeline.
- **Công việc chi tiết:**
  - Xây ChromaDB với `sentence-transformers/all-MiniLM-L6-v2` và ba collection độc lập.
  - Tiêm đủ sáu lỗi dữ liệu: drop latest, blank summary, text noise, truncated title, stale date và duplicate rows.
  - Điều phối baseline pipeline và self-healing pipeline phục hồi idempotent từ raw snapshot.
- **Kết quả:** `data/embeddings/`, `data/results/`, `data/reports/corruption_report.md`.
