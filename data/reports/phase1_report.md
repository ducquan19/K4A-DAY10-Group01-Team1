# Báo Cáo Pha 1 — Baseline Data Pipeline & Observability

> **Ngày thực hiện:** 2026-09-25  
> **Nguồn dữ liệu:** Crossref REST API  
> **Trạng thái Quality Gate:** ✅ ĐẠT (PASS)

---

## 1. Tổng Quan Thu Thập & Làm Sạch Dữ Liệu (Ingestion & Cleaning)

| Thông số | Giá trị |
| :--- | :--- |
| **Tổng số bản ghi thô (Raw Records)** | 24 |
| **Số bản ghi sau làm sạch (Clean Records)** | 24 |
| **Số bản ghi trùng lặp đã khử** | 0 |
| **Độ dài trung bình tóm tắt (Summary chars)** | 241.88 |
| **Bài báo mới nhất (Latest published)** | 2026-07-22 |
| **Bài báo cũ nhất (Oldest published)** | 2026-03-28 |

---

## 2. Kiểm Soát Chất Lượng Dữ Liệu (Great Expectations 1.x & Freshness SLA)

### 2.1. Kết Quả Great Expectations 1.x
- **Trạng thái tổng thể:** `PASSED`
- **Chế độ kiểm định:** Ephemeral Context (RAM-only)
- **Danh sách Expectations thực thi:**
  1. `ExpectTableRowCountToBeBetween`: Số dòng trong khoảng [5, 5000] $\rightarrow$ **PASS**
  2. `ExpectColumnValuesToNotBeNull`: Các cột `paper_id`, `title`, `text_for_embedding` không null $\rightarrow$ **PASS**
  3. `ExpectColumnValuesToBeUnique`: Khóa định danh `paper_id` duy nhất 100% $\rightarrow$ **PASS**
  4. `ExpectColumnValueLengthsToBeBetween`: Trường `summary` đạt độ dài tối thiểu ≥ 30 ký tự $\rightarrow$ **PASS**
  5. `ExpectColumnValueLengthsToBeBetween`: Trường `title` đạt độ dài tối thiểu ≥ 8 ký tự $\rightarrow$ **PASS**

### 2.2. Giám Sát Độ Tươi (Freshness SLA Monitoring)
- **Ngưỡng quy định SLA:** ≤ 180 ngày (bài báo cũ không được vượt quá 25% tổng số dữ liệu).
- **Số bài báo quá hạn (> 180 ngày):** 1 / 24 bài.
- **Tỷ lệ bài cũ (Stale ratio):** 4.2%.
- **Đánh giá SLA (`is_fresh`):** `✅ Đạt chuẩn Freshness`.

---

## 3. Đánh Giá Hiệu Năng RAG Baseline (Benchmark Evaluation)

Bộ câu hỏi benchmark gồm 10 câu hỏi đa dạng qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`).

| Chỉ số đánh giá (Metric) | Kết quả Baseline | Mục tiêu tối thiểu | Đánh giá |
| :--- | :---: | :---: | :---: |
| **Retrieval Hit Rate** | **100.00%** | ≥ 80.0% | ✅ Đạt |
| **Mean Token F1** | **1.0000** | ≥ 0.5000 | ✅ Đạt |
| **Judge Accuracy** | **100.00%** | ≥ 70.0% | ✅ Đạt |
| **Mean Judge Score (1-5)** | **5.00 / 5.0** | ≥ 3.0 | ✅ Đạt |

- **Judge backend:** `llm` — 10/10 lượt dùng LLM, 0/10 lượt fallback heuristic.

---

## 4. Kết Luận
Toàn bộ luồng dữ liệu sạch Pha 1 đã được kiểm định chất lượng nghiêm ngặt bởi Great Expectations 1.x và Freshness SLA trước khi nạp vào ChromaDB vector store. Hệ thống RAG đạt hiệu năng cơ sở cao, sẵn sàng cho các bài thử thách tiêm độc tố dữ liệu ở Pha 2.
