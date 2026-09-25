# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Team1`
- **Mã Nhóm / Lớp:** `K4-L3A`
- **Tên Repository Nộp Bài:** `K4A-DAY10-Group01-Team1`
- **Quy mô nhóm:** 2 thành viên

---

## Thành viên

| STT | Họ và tên | MSSV | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|
| 1 | | | Pipeline Lead, Integrator & RAG Specialist<br>*(`core/`, `phase1.py`, `corruption_flow.py`, `retrieval/index.py`, `embeddings.py`, ChromaDB)* | `report/<MSSV1>_HoTen.md` |
| 2 | Trần Đức Quân | 2A202602922 | Data Foundation, Observability & Evaluation Lead<br>*(`crossref.py`, `cleaning.py`, `quality.py` GX 1.x, `testset.py`, `reporting.py`)* | [`report/2A202602922_Tran_Duc_Quan.md`](../report/2A202602922_Tran_Duc_Quan.md) |

---

## Cá nhân

### ThanhVien1-MSSV1
- **Vai trò:** Pipeline Lead, Integrator & RAG Specialist.
- **Phạm vi trách nhiệm:**
  - Quản trị cấu hình `core/config.py`, đường dẫn artifacts `core/utils.py`, điều phối luồng `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Quản lý mô hình nhúng `all-MiniLM-L6-v2`, nạp và quản lý 3 collection ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`), xây dựng QA Agent truy vấn ngữ cảnh.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống và liên kết các pipeline end-to-end.
  - Quản lý cơ chế chuyển đổi LLM provider và kiểm thử truy vấn vector database.
  - Theo dõi tính nhất quán dữ liệu và đảm bảo commit contributor trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Thiết kế kiến trúc Idempotent Pipeline và cô lập không gian vector phục vụ đối chiếu công bằng giữa dữ liệu sạch và dữ liệu lỗi.

---

### Trần Đức Quân - 2A202602922
- **Vai trò:** Data Foundation, Observability & Evaluation Lead.
- **Phạm vi trách nhiệm:**
  - Ingestion & Raw Preservation (`src/ingestion/crossref.py`), làm sạch & chuẩn hóa feature cho embedding (`src/ingestion/cleaning.py`), cơ chế Idempotent Repair từ snapshot gốc.
  - Thiết lập Data Quality Gate chuẩn **Great Expectations 1.x** và giám sát Freshness SLA (`src/observability/quality.py`), xây dựng bộ test chuẩn 10 câu hỏi (`src/evaluation/testset.py`), xuất báo cáo markdown đối chiếu (`src/observability/reporting.py`).
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module cào Crossref API với Dual-Mode Fallback an toàn, bóc tách thẻ XML `<jats:p>` và lưu trữ 2 file raw artifacts.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` 5 phần, khử trùng lặp theo `paper_id`.
  - Cấu hình Ephemeral Context chuẩn GX 1.x với 4 Expectations cốt lõi, giám sát Freshness SLA (cảnh báo khi bài cũ > 180 ngày vượt quá 25%).
  - Thiết lập bộ benchmark test set 10 câu hỏi qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`).
  - Xây dựng logic sinh báo cáo Phase 1 và báo cáo đối chiếu 3 trạng thái Baseline vs Corrupted vs Repaired.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc bản chất hiện tượng Silent Failure trong RAG, tầm quan trọng của Data Lineage / Raw Preservation và cách dùng Great Expectations 1.x làm chốt kiểm soát chất lượng dữ liệu tự động.
