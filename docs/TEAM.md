# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Kẻ Độc Hành`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3A-Day10-Ke_Doc_Hanh`

---

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Tú Tài | 02455 | — | Pipeline Lead (`core/`, phase pipelines, corruption/repair integration) | `report/02455_NguyenTuTai.md` |
| 2 | Nguyễn Phú Bình | 02410 | — | Data Foundation Owner (`crossref.py`, `cleaning.py`, raw/clean artifacts) | `report/02410_NguyenPhuBinh.md` |
| 3 | Trần Đại Nhân | 02642 | — | RAG Specialist (MiniLM embeddings, ChromaDB, retrieval and QA agent) | `report/02642_TranDaiNhan.md` |
| 4 | Phan Văn Nghị | 02632 | — | Observability & Evaluation Lead (GX quality, freshness, benchmark and reporting) | `report/02632_PhanVanNghi.md` |

---

## Cá nhân

### Nguyễn Tú Tài - 02455

- **Vai trò:** Pipeline Lead, điều phối kiến trúc, tích hợp và vận hành luồng end-to-end.
- **Công việc chi tiết:**
  - Quản lý cấu hình `core/` và hợp nhất các module ingestion, quality, retrieval, evaluation thành pipeline thống nhất.
  - Điều phối `run_phase1.py` và `run_corruption_flow.py`, bảo đảm baseline, corrupted và repaired chạy end-to-end.
  - Rà soát tính idempotent, offline fallback và khả năng tái hiện toàn bộ bài lab.
- **Kết quả:** `src/core/`, `src/pipelines/`, `script/`, các artifacts tích hợp trong `data/`.

### Nguyễn Phú Bình - 02410

- **Vai trò:** Data Foundation Owner, phụ trách nguồn dữ liệu, chuẩn hóa và data lineage.
- **Công việc chi tiết:**
  - Bóc tách Crossref payload, chuẩn hóa DOI, tiêu đề, JATS abstract, tác giả, chuyên ngành và ngày ISO 8601.
  - Hoàn thiện cơ chế retry, xử lý 429 và offline fallback từ `data/raw/crossref_response.json`.
  - Xây dựng clean dataframe 24 dòng, tính `age_days`, khử trùng lặp và tạo `text_for_embedding` năm phần.
- **Kết quả:** `src/ingestion/`, `data/raw/`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`.

### Trần Đại Nhân - 02642

- **Vai trò:** RAG Specialist, phụ trách embedding, vector retrieval và QA agent.
- **Công việc chi tiết:**
  - Xây ChromaDB với `sentence-transformers/all-MiniLM-L6-v2` và các collection độc lập theo trạng thái dữ liệu.
  - Hoàn thiện semantic search, truy xuất top-k và logic QA dựa trên tài liệu được tìm thấy.
  - Kiểm tra tác động của dữ liệu bẩn và dữ liệu repaired lên retrieval hit rate, token F1 và câu trả lời.
- **Kết quả:** `src/retrieval/`, `data/embeddings/`, các Chroma collections và retrieval metrics.

### Phan Văn Nghị - 02632

- **Vai trò:** Observability & Evaluation Lead, phụ trách quality gate, freshness, benchmark và báo cáo.
- **Công việc chi tiết:**
  - Thiết lập Great Expectations 1.x bằng ephemeral context, kiểm tra row count, null, unique và độ dài summary.
  - Theo dõi freshness SLA và xây dựng benchmark năm loại câu hỏi dùng chung cho ba trạng thái dữ liệu.
  - Tổng hợp baseline/corrupted/repaired metrics, xác minh artifacts và sinh báo cáo Markdown đối chiếu.
- **Kết quả:** `src/observability/`, `src/evaluation/`, `data/quality/`, `data/eval/`, `data/reports/`.
