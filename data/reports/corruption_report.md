# Báo Cáo Đối Chiếu 3 Trạng Thái — Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Chứng minh hiện tượng Silent Failure khi RAG gặp dữ liệu bẩn, năng lực phát hiện của Data Quality Gate (Great Expectations 1.x) và hiệu quả phục hồi toàn vẹn từ nguồn Raw (Idempotent Repair).

---

## 1. Bảng Tổng Hợp Chỉ Số Hiệu Năng 3 Trạng Thái

| Chỉ số / Tín hiệu kiểm soát | 🟢 Baseline (Sạch) | 🔴 Corrupted (Bị tiêm lỗi) | 🔵 Repaired (Sau phục hồi) | Nhận xét xu hướng |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.00%** | **50.00%** | **100.00%** | Corruption: -50.00%; repair: +50.00% |
| **Mean Token F1** | **1.0000** | **0.5506** | **1.0000** | Corruption: -0.4494; repair: +0.4494 |
| **Judge Accuracy** | **100.00%** | **40.00%** | **100.00%** | So sánh định lượng từ cùng test set |
| **Mean Judge Score (1-5)** | **5.00** | **3.30** | **5.00** | Không giả định mức phục hồi trước khi đo |
| **Judge backend** | **llm** | **llm** | **llm** | Phân biệt LLM thật với heuristic fallback |
| **Quality Gate Status (GX 1.x)** | **PASS** | **FAIL (Phát hiện lỗi)** | **PASS** | GX phát hiện vi phạm tính duy nhất & độ dài |
| **Freshness SLA Status** | **PASS** | **ALERT (Quá hạn SLA)** | **PASS** | Báo động khi bài báo bị lùi ngày quá hạn |
| **Số lượng bài báo quá hạn** | N/A | 9 dòng | 1 dòng | Đối chiếu từ freshness artifacts |

---

## 2. Chi Tiết 6 Dạng Lỗi Dữ Liệu Tiêm Vào (Corruption Scenarios)

1. **Drop latest records (Mất 20% bản ghi mới):** Làm biến mất các tài liệu nghiên cứu mới nhất, dẫn đến câu hỏi về các bài báo này hoàn toàn bị miss (`Retrieval Hit Rate` sụt giảm).
2. **Blank summary (Xóa rỗng tóm tắt):** Một số bài báo bị mất hoàn toàn phần tóm tắt, khiến embedding vector bị nghèo nàn thông tin và vi phạm `ExpectColumnValueLengthsToBeBetween(min_value=30)`.
3. **Inject noise (Chèn ký tự rác):** Chèn các chuỗi vô nghĩa làm biến dạng không gian vector và làm loãng ngữ cảnh trả lời của LLM.
4. **Truncate title (Cắt ngắn tiêu đề < 8 ký tự):** Gây mất mát thông tin nhận diện tài liệu, vi phạm expectation kiểm tra độ dài tiêu đề tối thiểu.
5. **Stale date (Lùi ngày xuất bản về quá khứ):** Mô phỏng dữ liệu bị lỗi thời (> 180 ngày), kích hoạt cảnh báo `is_fresh = False` của Freshness SLA.
6. **Duplicate rows (Nhân bản bản ghi):** Tạo các bản ghi trùng `paper_id`, vi phạm trực tiếp expectation `ExpectColumnValuesToBeUnique`.

---

## 3. Hiện Tượng Silent Failure & Tầm Quan Trọng Của Observability

- **Hành vi của Agent khi dữ liệu bị lỗi:** Mã nguồn hệ thống RAG không hề ném ra Exception hay dừng chương trình (`exit code 0`). Tuy nhiên, câu trả lời của AI trở nên sai lệch, ảo giác (hallucination) hoặc không tìm thấy tài liệu liên quan.
- **Vai trò của Data Quality Gate (GX 1.x):** Chốt chặn GX 1.x và Freshness SLA đã lập tức gióng chuông cảnh báo đỏ ngay tại tầng dữ liệu, ngăn chặn việc phục vụ dữ liệu lỗi ra production.

---

## 4. Cơ Chế Phục Hồi Dữ Liệu An Toàn (Idempotent Repair)

- **Nguyên lý:** Nhờ bảo toàn bản sao thô ban đầu bất biến tại `data/raw/crossref_records.json`, quá trình sửa chữa được kích hoạt bằng cách chạy lại toàn bộ pipeline làm sạch từ nguồn gốc tin cậy.
- **Tính Idempotent:** Quy trình repair có thể thực thi lặp lại nhiều lần mà vẫn tạo ra kết quả đồng nhất và sạch 100%, loại bỏ hoàn toàn mọi tàn dư của dữ liệu độc hại mà không cần can thiệp thủ công.
- **Kết quả nghiệm thu:** Kết quả repair được chấp nhận khi Quality Gate trở lại PASS và các metrics tiến gần hoặc bằng Baseline; các giá trị thực tế nằm trong bảng trên.
