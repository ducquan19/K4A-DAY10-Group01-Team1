# Báo cáo nhóm — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | Team1 |
| Repository | `https://github.com/ducquan19/K4A-DAY10-Group01-Team1` |
| Ngày hoàn thành | 2026-09-25 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Bùi Đình Đề | 2A202602818 | Pipeline Lead, Integrator & RAG Specialist | `core/`, `retrieval/`, `pipelines/`, corruption integration, ChromaDB, tests |
| 2 | Trần Đức Quân | 2A202602922 | Data Foundation, Observability & Evaluation Lead | Crossref ingestion, cleaning, GX/Freshness, test set và reporting |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thiện pipeline RAG hai pha sử dụng 24 metadata bài báo Crossref, hỗ trợ API trực tiếp và snapshot offline. Pha baseline bảo toàn raw lineage, chuẩn hóa dữ liệu, kiểm định bằng Great Expectations 1.x và Freshness SLA trước khi tạo vector 384 chiều bằng `all-MiniLM-L6-v2` và lưu vào ChromaDB. Bộ benchmark cố định gồm 10 câu hỏi thuộc bốn nhóm summary, authors, date và categories. Baseline đạt Retrieval Hit Rate 100%, Mean Token F1 1.0000, Judge Accuracy 100% và Quality Gate 7/7 PASS.

Pha corruption tiêm deterministic sáu dạng lỗi: bỏ 5 records mới nhất, xóa 2 summaries, chèn noise vào 3 summaries, cắt 2 titles, làm cũ ngày của 6 records và thêm 2 duplicate rows. Quality Gate chuyển sang FAIL, stale ratio tăng từ 4.17% lên 42.86%, Hit Rate giảm còn 50% và Token F1 còn 0.5506. Quality/Freshness failure tự động kích hoạt repair từ raw snapshot; các metrics trở lại baseline và GX/Freshness PASS. Cả ba trạng thái đều được OpenRouter `openai/gpt-4o-mini` chấm đủ 10/10 mẫu, không dùng heuristic fallback. Ragas không chạy mặc định để giới hạn chi phí/thời gian. Cảnh báo cleanup thư mục tạm của GX trên Windows sandbox không ảnh hưởng exit code hoặc artifacts.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref API / data/raw/crossref_response.json
    -> parse PaperRecord và giữ raw lineage
    -> cleaning, deduplicate, age_days, text_for_embedding
    -> Great Expectations 1.x + Freshness SLA
    -> MiniLM embedding + ChromaDB papers-baseline
    -> fixed test_set.json + baseline metrics
    -> six deterministic corruptions
    -> papers-corrupted + quality alert + degraded metrics
    -> rebuild từ crossref_records.json
    -> papers-repaired + recovered metrics
    -> corruption_report.md
```

| Khối | Input | Xử lý | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API/snapshot | Retry, fallback, parse và preserve raw | `data/raw/*.json` | Trần Đức Quân |
| Cleaning | `PaperRecord` | Normalize, deduplicate, `age_days`, embedding text | `data/clean/papers_clean.*` | Trần Đức Quân |
| Observability | Clean/corrupted/repaired DataFrame | 7 GX checks và Freshness SLA | `data/quality/*.json` | Trần Đức Quân |
| Evaluation | Clean DataFrame | 10 fixed questions, Hit Rate, Token F1, Judge | `data/eval/`, `data/results/` | Trần Đức Quân |
| Embedding/index | `text_for_embedding` | MiniLM 384 chiều, cosine search | Ba Chroma collections | Bùi Đình Đề |
| Corruption/repair | Clean DataFrame/raw lineage | Sáu lỗi và rebuild từ raw | Corruption log, corrupted/repaired data | Bùi Đình Đề |
| Orchestration | Tất cả module | Quality gate, index, evaluate, report | Hai pipeline và reports | Bùi Đình Đề |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openrouter` |
| `LLM_MODEL` | `openai/gpt-4o-mini` |
| Judge provenance | LLM thật 10/10 mẫu ở cả Baseline, Corrupted và Repaired; fallback 0 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày; stale ratio tối đa 25% |
| Corruption selection | Deterministic fixed slices, không dùng random seed |

### Lệnh chạy

```powershell
python -m pip install -e ".[dev]"
$env:HF_HUB_OFFLINE="1"
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --cov=src --cov-report=term-missing
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

| Lệnh | Trạng thái | Thời điểm gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Unit/integration tests | Thành công, 22/22; coverage 84.41% | 2026-09-25 | `tests/`, `pyproject.toml`, GitHub Actions |
| Baseline pipeline | Thành công, exit code 0 | 2026-09-25 | `baseline_metrics.json`, `phase1_report.md` |
| Corruption flow | Thành công, exit code 0 | 2026-09-25 | `corruption_log.json`, ba metrics và `corruption_report.md` |

## 5. Ingestion, cleaning và data contract

| Thuộc tính | Giá trị |
| --- | --- |
| Endpoint | `https://api.crossref.org/works` hoặc local snapshot |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:<run_date-180>,has-abstract:true` |
| Records | 24 raw, 24 clean |
| Retry/fallback | Retry cho 429/503; fallback về raw snapshot |

| Trường | Kiểu | Bắt buộc | Ý nghĩa/xử lý |
| --- | --- | --- | --- |
| `paper_id` | string | Có | DOI, khóa deduplicate và document identity |
| `title` | string | Có | Normalize whitespace, title phải dài tối thiểu 8 ở quality gate |
| `summary` | string | Có | Loại JATS/XML, tối thiểu 30 ký tự |
| `authors_joined` | string | Có | Danh sách tác giả đã nối |
| `categories_joined` | string | Có | Các subject/category đã nối |
| `published` | ISO date | Có | Dùng tính freshness và trả lời date |
| `age_days` | integer | Có | `run_date - published` |
| `text_for_embedding` | string | Có | Title + Authors + Published + Categories + Summary |

Cleaning giữ nguyên 24/24 records và loại 0 duplicate. `paper_id` ổn định xuyên suốt ba trạng thái; Chroma `record_id` thêm row index để có thể quan sát duplicate rows trong corrupted collection.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| `question_type` | 3 summary, 3 authors, 2 date, 2 categories |
| Ground truth ID | DOI từ `paper_id` của clean record |
| Embedding | MiniLM-L6-v2, normalized, 384 chiều |
| Vector store | Chroma cosine; `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval | `top_k=4` |
| Test set | `data/eval/test_set.json` dùng chung cả ba trạng thái |

Giữ nguyên test set giúp kiểm soát độ khó câu hỏi; mọi thay đổi metrics phản ánh biến đổi corpus thay vì thay đổi đề đánh giá.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn | Trạng thái |
| --- | --- | --- |
| Raw response/records | `data/raw/` | Có |
| Cleaned dataset | `data/clean/papers_clean.csv/json` | Có |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có |
| Evaluation set | `data/eval/test_set.json` | Có, 10 câu |
| Baseline metrics/answers | `data/results/baseline_*.json` | Có |
| Auto-repair evidence | `data/results/repair_log.json` | Có; tự động kích hoạt bởi GX và Freshness |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Có |
| Baseline report | `data/reports/phase1_report.md` | Có |

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| Retrieval Hit Rate | 1.0000 | Ground-truth DOI xuất hiện trong top-4 ở 10/10 câu |
| Mean Token F1 | 1.0000 | Deterministic QA khớp ground truth trên clean corpus |
| Judge Accuracy | 1.0000 | 10/10 câu được đánh giá đúng |
| Mean Judge Score | 5.00/5 | OpenRouter LLM judge, 10/10 lượt; fallback 0 |
| Ragas | Skipped | Chỉ chạy khi `RUN_RAGAS=1` do chi phí/thời gian |

## 8. Data quality và freshness

| Check | Ngưỡng | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- | --- |
| Row count | 5–5000 | PASS, 24 | PASS, 21 | PASS, 24 |
| Required not-null | ID/title/embedding text | PASS | PASS | PASS |
| Unique `paper_id` | 100% | PASS | FAIL | PASS |
| Summary length | ≥30 | PASS | FAIL | PASS |
| Title length | ≥8 | PASS | FAIL | PASS |
| Tổng GX | Tất cả pass | 7/7 PASS | 4/7, overall FAIL | 7/7 PASS |

| Freshness | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Latest published | 2026-07-22 | 2026-06-07 | 2026-07-22 |
| Stale rows | 1/24 | 9/21 | 1/24 |
| Stale ratio | 4.17% | 42.86% | 4.17% |
| Status | PASS | ALERT | PASS |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Tác động | Quality signal |
| --- | --- | ---: | --- |
| Drop latest | Bỏ 20% mới nhất | 5 records | Retrieval miss cho tài liệu bị xóa |
| Blank summary | Gán summary rỗng | 2 records | Summary length FAIL |
| Inject noise | Chèn marker rác 8 lần | 3 records | Embedding/context bị nhiễu |
| Truncate title | Cắt còn 7 ký tự | 2 records | Title length FAIL |
| Stale date | Lùi 365 ngày | 6 records | Freshness ALERT |
| Duplicate rows | Thêm một copy | 2 records | Unique ID FAIL |

Corruption log tại `data/results/corruption_log.json` có đủ type, số lượng, paper IDs và parameters. Sau drop và duplicate, corrupted dataset có 21 rows.

Repair đọc lại `data/raw/crossref_records.json`, gọi cùng cleaning function và tạo collection `papers-repaired`; không đọc hoặc vá corrupted dataset. `repair_log.json` ghi `triggered_automatically=true`, hai nguyên nhân `data_quality_gate_failed` và `freshness_sla_failed`, cùng kết quả 24 dòng, Quality/Freshness PASS. Chạy Phase 2 lặp lại vẫn giữ 24 repaired documents và metrics trở về baseline.

## 10. So sánh ba trạng thái

| Metric/signal | Baseline | Corrupted | Repaired | Tác động corruption | Phục hồi |
| --- | ---: | ---: | ---: | ---: | ---: |
| Retrieval Hit Rate | 1.0000 | 0.5000 | 1.0000 | -0.5000 | +0.5000 |
| Mean Token F1 | 1.0000 | 0.5506 | 1.0000 | -0.4494 | +0.4494 |
| Judge Accuracy | 1.0000 | 0.4000 | 1.0000 | -0.6000 | +0.6000 |
| Mean Judge Score | 5.00 | 3.30 | 5.00 | -1.70 | +1.70 |
| Quality Gate | PASS | FAIL | PASS | 3 checks fail | Phục hồi 7/7 |
| Freshness | PASS | ALERT | PASS | +38.69 điểm % stale | Về 4.17% |

Quan hệ nhân quả có bằng chứng:

1. Drop latest records và làm hỏng nội dung/identity → GX/Freshness phát hiện vi phạm → Hit Rate giảm 50 điểm phần trăm và Token F1 giảm 0.4494.
2. Rebuild từ immutable raw lineage → GX/Freshness trở lại PASS → toàn bộ bốn metrics trở lại đúng mức baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Agent dùng provider `mock` lỗi `NotImplementedError` tại `bind_tools()`.
- **Nguyên nhân:** `FakeListChatModel` không triển khai tool binding mà `create_agent` yêu cầu.
- **Cách xử lý:** Tạo `MockPaperAgent` tương thích `invoke()`, sử dụng retrieval/QA deterministic và không cần credential.
- **Cách xác minh:** Test mock-agent pass; toàn bộ 22/22 tests pass, coverage 84.41%.

Ngoài ra, manifest Chroma ban đầu lưu absolute path. Nhóm chuyển thành `data/chroma` tương đối và resolve theo project root để repository portable.

## 12. Giới hạn và hướng cải thiện

| Giới hạn | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Ragas mặc định tắt | Chưa có faithfulness/context precision từ Ragas | Chạy `RUN_RAGAS=1` và lưu kết quả khi có evaluator ổn định |
| Heuristic fallback vẫn tồn tại khi provider lỗi | Có thể giảm độ độc lập của Judge trong môi trường offline | Metrics ghi rõ `judge_backend`, `llm_judge_samples`, `fallback_judge_samples`; lần nghiệm thu fallback = 0 |
| GX temp cleanup warning trên Windows sandbox | Log nhiễu nhưng pipeline không fail | Đặt GX temp directory có ACL phù hợp hoặc chạy ngoài sandbox |
| Corruption dùng fixed slices | Reproducible nhưng chưa phủ phân phối lỗi ngẫu nhiên | Chạy nhiều seed và báo cáo mean/std degradation |

## 13. Đối chiếu thang điểm

| Tiêu chí rubric | Điểm tối đa | Bằng chứng chính | Tự đánh giá |
| --- | ---: | --- | ---: |
| Cấu trúc dự án & môi trường | 10 | `pyproject.toml`, module `src/`, smoke test import | 10 |
| Raw ingestion & lineage | 15 | `crossref.py`, hai raw JSON artifacts, API/fallback | 15 |
| Cleaning & pre-embed | 15 | 24 dòng sạch, deduplicate, `age_days`, embedding text 5 phần | 15 |
| Embedding & vector store | 10 | MiniLM 384 chiều; Chroma 24/21/24 documents | 10 |
| Multi-provider QA Agent | 10 | Router 7 provider modes; OpenRouter Agent smoke test thành công | 10 |
| Baseline evaluation | 10 | 10 câu/4 loại; Hit Rate và Token F1 artifacts | 10 |
| GX 1.x & Freshness SLA | 15 | 7 checks; PASS/FAIL/PASS và stale ratio 4.17%/42.86%/4.17% | 15 |
| Corruption, repair & impact | 15 | 6 lỗi; metrics suy giảm/phục hồi; báo cáo 3 trạng thái | 15 |
| **Tổng bắt buộc** | **100** | Tất cả artifact bắt buộc tồn tại | **100** |

Đây là tự đánh giá dựa trên artifacts và lệnh nghiệm thu, không thay thế kết quả chấm chính thức.

## 14. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp module, artifact và kết quả thực tế.
- [x] Hai pipeline và 22 tests đã chạy lại; coverage 84.41%.
- [x] Ba trạng thái dùng cùng evaluation set.
- [x] Bảng metrics khớp các file trong `data/results/`.
- [x] Kết luận Quality/Freshness khớp `data/quality/`.
- [x] Đường dẫn báo cáo và artifacts tồn tại.
- [x] Mỗi thành viên có báo cáo cá nhân.
- [x] Không có `.env`, API key hoặc token trong tracked source/report.

## 15. Bằng chứng điểm bonus

| Hạng mục | Bằng chứng | Kết quả |
| --- | --- | --- |
| B2 — Automated Self-Healing | `corruption_flow.py`, `data/results/repair_log.json` | GX/Freshness tự động phát hiện lỗi và kích hoạt rebuild từ immutable raw lineage; repair PASS |
| B3 — Pytest CI & coverage | `.github/workflows/tests.yml`, `pyproject.toml`, 22 tests | CI Python 3.11/3.13; coverage gate 80%; đo thực tế 84.41% |

Hai hạng mục trên cung cấp bằng chứng cho tối đa 10 điểm bonus theo `docs/RUBRIC.md`.
