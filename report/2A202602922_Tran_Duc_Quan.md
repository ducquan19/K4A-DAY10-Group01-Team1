# Member Role Report — Day 10: Data Pipeline & Data Observability
## Báo Cáo Cá Nhân

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | Trần Đức Quân |
| **MSSV** | 2A202602922 |
| **Khóa/Lớp** | K4 - L3A |
| **Tên nhóm** | Team1 |
| **Vai trò chính** | Data Foundation, Observability & Evaluation Lead |
| **Repository** | `ducquan19/K4A-DAY10-Group01-Team1` |
| **Ngày hoàn thành** | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

Nhóm gồm **2 thành viên**, tôi đảm nhận toàn bộ 2 khối công việc trọng tâm về **Tầng Dữ Liệu** và **Kiểm Soát Chất Lượng & Đánh Giá**.

### Phần việc sở hữu (Ownership)

| Khối nhiệm vụ | Module / Deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ingestion & Lineage** | Thu thập dữ liệu Crossref và bảo toàn bản gốc | `src/ingestion/crossref.py`<br>- `parse_crossref_payload()`<br>- `fetch_source_records()`<br>- `load_raw_records()` | Crossref REST API hoặc snapshot local `crossref_response.json` | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` (24 đối tượng `PaperRecord`) | Hoàn thành (Passed CP0 verification) |
| **Data Cleaning & Pre-embed** | Làm sạch text, tính `age_days`, ghép `text_for_embedding`, khử trùng lặp | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe()` | List `PaperRecord`, `run_date` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` (24 dòng sạch, đủ 16 cột schema) | Hoàn thành (Passed CP1 verification) |
| **Quality Gate (GX 1.x)** | Thiết lập chốt kiểm dịch chất lượng tự động | `src/observability/quality.py`<br>- `run_data_quality_checks()` | Cleaned DataFrame `papers_clean.csv/json`, Settings | Ephemeral GX 1.x Context, báo cáo `baseline_quality_report.json` và `corrupted_quality_report.json` | Hoàn thành (Passed CP1 verification, `status=True`) |
| **Freshness SLA** | Giám sát độ tươi dữ liệu khoa học | `src/observability/quality.py`<br>- `build_freshness_report()` | Cleaned DataFrame chứa cột `age_days`, ngưỡng SLA (180 ngày) | Báo cáo `data/quality/freshness_report.json` (`is_fresh=True`, tỷ lệ bài cũ $\le 25\%$) | Hoàn thành |
| **Evaluation Benchmark** | Xây dựng bộ đề thi chuẩn 10 câu hỏi qua 4 nhóm nghiệp vụ | `src/evaluation/testset.py`<br>- `build_test_set()` | Cleaned DataFrame | File `data/eval/test_set.json` (10 câu hỏi đa dạng `summary`, `authors`, `date`, `categories`) | Hoàn thành (Passed CP2 verification, đủ 10 câu) |
| **Markdown Reporting** | Tự động xuất báo cáo Pha 1 và báo cáo đối chiếu 3 trạng thái | `src/observability/reporting.py`<br>- `generate_phase1_report()`<br>- `generate_corruption_report()` | Metrics và kết quả kiểm định của 3 trạng thái | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Hoàn thành |

### Việc phối hợp với thành viên còn lại

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Cung cấp dữ liệu sạch cho Vector Database | `src/retrieval/index.py` | Đảm bảo DataFrame đầu ra có đầy đủ `text_for_embedding` và các metadata lồng ghép (`authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url`) để nạp vào ChromaDB collection `papers-baseline`. |
| Cung cấp bộ benchmark và ground-truth IDs | `src/evaluation/metrics.py` | Đảm bảo `data/eval/test_set.json` có đúng định dạng chuẩn để hàm `evaluate_pipeline()` đo lường chính xác `retrieval_hit_rate` và `mean_token_f1`. |
| Kết nối Quality Gate vào Pipeline điều phối | `src/pipelines/phase1.py` & `src/pipelines/corruption_flow.py` | Cung cấp interface hàm `run_data_quality_checks()` và `build_freshness_report()` trả về kết quả chuẩn dict để pipeline dễ dàng ghi nhận và ra quyết định. |

---

## 3. Kết quả theo vai trò & Bằng chứng nghiệm thu

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Lệnh xác minh & Tín hiệu hoàn thành |
| :--- | :--- | :--- | :--- |
| **CP0:** Ingestion & Dual-Mode Fallback | `src/ingestion/crossref.py` | 24 `PaperRecord` chuẩn hóa | `python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"`<br>$\rightarrow$ **Tín hiệu hoàn thành: Đã tải 24 bài báo** ✅ |
| **CP1:** Cleaning, `age_days`, `text_for_embedding` | `src/ingestion/cleaning.py` | DataFrame 24 dòng sạch | `python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"`<br>$\rightarrow$ **Tín hiệu hoàn thành: Clean thành công 24 dòng** ✅ |
| **CP1:** Data Quality Gate GX 1.x & Freshness | `src/observability/quality.py` | Quality Gate chạy thành công với 4 Expectations và Freshness check | `python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); status=res.get('success'); print(f'Tín hiệu hoàn thành: Quality check status = {status}')"`<br>$\rightarrow$ **Tín hiệu hoàn thành: Quality check status = True** ✅ |
| **CP2:** Benchmark Test Set 10 câu hỏi | `src/evaluation/testset.py` | File `test_set.json` (10 câu hỏi qua 4 nhóm) | `python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); count=len(ts); print(f'Tín hiệu hoàn thành: Sinh được {count} câu hỏi test')"`<br>$\rightarrow$ **Tín hiệu hoàn thành: Sinh được 10 câu hỏi test** ✅ |
| **CP3-CP5:** Markdown Reporting | `src/observability/reporting.py` | `phase1_report.md` & `corruption_report.md` | Báo cáo Markdown có bảng so sánh đầy đủ 3 trạng thái. |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### 4.1. Vấn đề cần giải quyết
1. **Raw Preservation (Bảo toàn nguồn gốc dữ liệu):** Thu thập API bên ngoài dễ gặp sự cố rớt mạng hoặc `429 Too Many Requests`. Nếu không lưu bản sao thô ban đầu nguyên vẹn, ta sẽ không thể tái lập hay tự động sửa chữa dữ liệu khi bước làm sạch gặp lỗi.
2. **Text Normalization & Noise Cleaning:** Dữ liệu học thuật Crossref chứa các thẻ XML JATS (`<jats:p>`), khoảng trắng thừa và cấu trúc tác giả lồng nhau cần được làm sạch triệt để.
3. **Chặn đứng Silent Failure trước serving:** Trong RAG, nếu dữ liệu bị lỗi (rỗng tóm tắt, trùng lặp ID, tiêu đề bị cắt), hệ thống phần mềm thông thường không hề báo lỗi crash mà âm thầm làm suy giảm chất lượng câu trả lời của AI. Cần một chốt kiểm soát tự động phát hiện trước khi dữ liệu đi vào Vector Store.
4. **Chuẩn hóa Great Expectations 1.x:** Tránh sử dụng cú pháp GX cũ (`context.sources.pandas_default`) vốn đã bị deprecated và gây lỗi runtime trên Great Expectations 1.16+.
5. **Freshness SLA Monitoring:** Kiến thức khoa học có tính thời gian, cần cơ chế phát hiện khi tỷ lệ tài liệu quá hạn (> 180 ngày) vượt quá 25%.

### 4.2. Cách triển khai kỹ thuật
- **`src/ingestion/crossref.py`:**
  - Bóc tách payload bằng regex loại bỏ sạch sẽ thẻ JATS: `re.sub(r"<[^>]+>", " ", abstract)`.
  - Format tác giả: `f"{given} {family}".strip()`.
  - Cơ chế Dual-Mode: Thử kết nối live API có retry 3 lần; nếu thất bại hoặc cấu hình offline thì tự động fallback đọc snapshot `crossref_response.json`.
- **`src/ingestion/cleaning.py`:**
  - Tính `age_days = (run_date - published).days`.
  - Ghép trường `text_for_embedding` gồm 5 phần chuẩn: `Title`, `Authors`, `Published`, `Categories`, `Summary`.
  - Khử trùng lặp bản ghi theo khóa duy nhất `paper_id` và lọc bỏ các bản ghi thiếu trường dữ liệu cốt lõi.
- **`src/observability/quality.py`:**
  - Cấu hình Ephemeral Context GX 1.x chạy trên RAM:
    ```python
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    ```
  - Triển khai 4 Expectations cốt lõi:
    1. `ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)`
    2. `ExpectColumnValuesToNotBeNull` (`paper_id`, `title`, `text_for_embedding`)
    3. `ExpectColumnValuesToBeUnique` (`paper_id`)
    4. `ExpectColumnValueLengthsToBeBetween` (`summary` $\ge 30$)
    5. Bổ sung `ExpectColumnValueLengthsToBeBetween` (`title` $\ge 8$) để bắt lỗi truncate title.
  - Tính toán Freshness SLA: Cảnh báo `is_fresh = False` nếu tỷ lệ bài báo có `age_days > 180` vượt quá 25%.
- **`src/evaluation/testset.py`:**
  - Sinh 10 câu hỏi đa dạng qua 4 nhóm nghiệp vụ (`summary`: 3 câu, `authors`: 3 câu, `date`: 2 câu, `categories`: 2 câu), trích xuất `ground_truth` và `ground_truth_doc_ids` phục vụ đánh giá tự động.
- **`src/observability/reporting.py`:**
  - Tự động sinh báo cáo Markdown Pha 1 và báo cáo đối chiếu 3 trạng thái với bảng so sánh định lượng rõ ràng.

---

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp khởi tạo context trong Great Expectations 1.x (`ephemeral` trên bộ nhớ RAM vs `file` lưu trữ trên đĩa).
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Khởi tạo file context cố định trên đĩa (`gx/great_expectations.yml`).
  2. *Phương án 2 (Được chọn):* Sử dụng `gx.get_context(mode="ephemeral")` chạy hoàn toàn trên RAM.
- **Lý do:** Chế độ `ephemeral` giúp việc kiểm định diễn ra nhanh chóng, nhẹ nhàng, không sinh ra các file rác trong repo Git, và tương thích 100% với môi trường CI/CD không trạng thái (stateless).

---

## 6. Lỗi / Blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>` khi chạy lệnh kiểm tra trên PowerShell Windows console.
- **Nguyên nhân gốc:** Bảng mã mặc định của Windows PowerShell là `cp1252`, không tương thích với các chuỗi ký tự UTF-8 tiếng Việt khi in ra stdout.
- **Cách xử lý:** Đặt biến môi trường `$env:PYTHONIOENCODING="utf-8"` trước khi thực thi script Python và đảm bảo mọi thao tác đọc/ghi file đều chỉ định rõ `encoding="utf-8"`.
- **Cách xác minh sau khi sửa:** Tất cả các lệnh kiểm tra CP0, CP1, CP2 đều in ra màn hình đúng định dạng và thành công 100%.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu từ Crossref API được tải về lưu nguyên bản vào `data/raw/crossref_response.json`, sau đó bóc tách thành danh sách `PaperRecord` tại `crossref_records.json`. Tiếp theo, module cleaning làm sạch text, tính `age_days`, ghép `text_for_embedding`, xuất ra `papers_clean.csv/json`. Dữ liệu sạch này bắt buộc phải đi qua Data Quality Gate (GX 1.x) để kiểm tra: chỉ khi Quality Gate báo `PASS`, dữ liệu mới được đưa vào mô hình nhúng `all-MiniLM-L6-v2` để sinh vector và lưu vào ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Hệ thống dùng 10 câu hỏi chuẩn có sẵn đáp án `ground_truth` và ID bài báo `ground_truth_doc_ids`. Khi Agent truy xuất top 4 tài liệu: nếu ID đúng nằm trong top 4 thì `retrieval_hit = True` (tính ra Hit Rate); câu trả lời của Agent được so sánh Token F1 với câu tóm tắt chuẩn và được LLM Judge chấm điểm trên thang 1-5.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks đo lường tính toàn vẹn của dữ liệu tại chỗ (không null, độ dài hợp lệ, không trùng ID), còn Freshness SLA đo lường độ trễ tri thức theo dòng thời gian (bài báo quá 180 ngày). Một bản ghi có thể rất sạch về mặt cú pháp nhưng vẫn bị coi là "hết hạn sử dụng" nếu tri thức đã cũ.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Dùng cùng một bộ đề thi duy nhất giúp loại trừ hoàn toàn các yếu tố nhiễu về độ khó câu hỏi, đảm bảo rằng mọi biến thiên về điểm số đều phản ánh chính xác 100% tác động của chất lượng dữ liệu.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên:
   - `data/reports/corruption_report.md`: Bảng so sánh 3 cột thể hiện sự phục hồi.
   - `data/results/repaired_metrics.json`: `retrieval_hit_rate` và `mean_token_f1` phục hồi về mức Baseline.
   - `data/quality/baseline_quality_report.json`: Quality check và Freshness SLA đều trả về `True`.

---

## 8. Điều học được và cam kết

- **Điều học được:** Nhận thức rõ ràng rằng trong sản phẩm AI thực tế, 60-80% thời gian là xử lý và kiểm soát chất lượng dữ liệu. Data Observability là tấm khiên bảo vệ AI Agent khỏi hiện tượng Silent Failure.
- **Cam kết:** Báo cáo phản ánh trung thực toàn bộ phần việc đã tự thực hiện, mã nguồn chạy thực tế không lỗi, và bản thân có thể tự tin thuyết trình toàn bộ quy trình trước lớp.

**Họ và tên:** [Thành viên 2]
**Ngày xác nhận:** 2026-09-25
