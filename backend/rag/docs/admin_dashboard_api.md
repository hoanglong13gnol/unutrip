\# SmartTravel RAG v2 - Admin Dashboard API



Base URL:



```text

http://127.0.0.1:8001

```



---



\# 1. System Overview



\## GET `/admin/system/overview`



Dùng cho trang tổng quan dashboard.



```powershell

curl.exe "http://127.0.0.1:8001/admin/system/overview"

```



Trả về các nhóm chính:



```json

{

&nbsp; "service": "SmartTravel RAG v2",

&nbsp; "runtime": {

&nbsp;   "runtime\_mode": "retrieval\_only",

&nbsp;   "enable\_gemini": false,

&nbsp;   "enable\_lora": false,

&nbsp;   "enable\_validator": false,

&nbsp;   "gemini\_configured": true

&nbsp; },

&nbsp; "rag": {

&nbsp;   "ready": true,

&nbsp;   "using\_reviewed": true

&nbsp; },

&nbsp; "cache": {

&nbsp;   "enabled": true,

&nbsp;   "records\_in\_memory": 0

&nbsp; },

&nbsp; "ai\_metrics": {

&nbsp;   "total\_requests": 31,

&nbsp;   "fallback\_rate": 0.8065

&nbsp; },

&nbsp; "data\_quality": {

&nbsp;   "place\_count": 5592,

&nbsp;   "issue\_count": 3315,

&nbsp;   "autofix\_changed\_count": 153,

&nbsp;   "reviewed\_exists": true

&nbsp; }

}

```



Dashboard nên hiển thị:



```text

\- Runtime mode

\- RAG ready

\- Using reviewed dataset

\- AI request count

\- Fallback rate

\- Cache status

\- Data quality issue count

\- Autofix count

```



---



\# 2. System Self Test



\## GET `/admin/system/self-test`



Dùng trước khi demo/báo cáo để kiểm tra hệ thống.



```powershell

curl.exe "http://127.0.0.1:8001/admin/system/self-test"

```



Response mẫu:



```json

{

&nbsp; "service": "SmartTravel RAG v2",

&nbsp; "ready": true,

&nbsp; "passed": 8,

&nbsp; "failed": 0,

&nbsp; "checks": {

&nbsp;   "health\_ok": {

&nbsp;     "ok": true

&nbsp;   },

&nbsp;   "rag\_files\_ready": {

&nbsp;     "ok": true

&nbsp;   },

&nbsp;   "place\_store\_using\_reviewed": {

&nbsp;     "ok": true

&nbsp;   },

&nbsp;   "retrieve\_khanhhoa\_ok": {

&nbsp;     "ok": true

&nbsp;   },

&nbsp;   "retrieve\_hue\_ok": {

&nbsp;     "ok": true

&nbsp;   }

&nbsp; }

}

```



Khi báo cáo, chỉ cần thấy:



```text

ready = true

passed = 8

failed = 0

```



---



\# 3. Runtime Status



\## GET `/runtime/status`



Dùng để xem chế độ AI hiện tại.



```powershell

curl.exe "http://127.0.0.1:8001/runtime/status"

```



Response mẫu:



```json

{

&nbsp; "service": "SmartTravel RAG v2",

&nbsp; "runtime\_mode": "retrieval\_only",

&nbsp; "enable\_gemini": false,

&nbsp; "enable\_lora": false,

&nbsp; "enable\_validator": false,

&nbsp; "gemini\_configured": true,

&nbsp; "places\_master\_ready": true,

&nbsp; "places\_app\_ready": true,

&nbsp; "places\_app\_reviewed\_ready": true,

&nbsp; "rag\_documents\_ready": true,

&nbsp; "bm25\_index\_ready": true

}

```



---



\# 4. RAG Status



\## GET `/admin/rag/status`



Dùng để kiểm tra dữ liệu và index RAG.



```powershell

curl.exe "http://127.0.0.1:8001/admin/rag/status"

```



Response mẫu:



```json

{

&nbsp; "service": "SmartTravel RAG v2",

&nbsp; "ready": true,

&nbsp; "files": {

&nbsp;   "places\_master": {

&nbsp;     "exists": true,

&nbsp;     "size\_mb": 1.44

&nbsp;   },

&nbsp;   "places\_app": {

&nbsp;     "exists": true,

&nbsp;     "size\_mb": 20.18

&nbsp;   },

&nbsp;   "places\_app\_reviewed": {

&nbsp;     "exists": true,

&nbsp;     "size\_mb": 20.18

&nbsp;   },

&nbsp;   "rag\_documents": {

&nbsp;     "exists": true,

&nbsp;     "size\_mb": 34.82

&nbsp;   },

&nbsp;   "bm25\_index": {

&nbsp;     "exists": true,

&nbsp;     "size\_mb": 62.96

&nbsp;   }

&nbsp; }

}

```



---



\# 5. Place Detail



\## GET `/admin/rag/place/{place\_id}`



Dùng để xem chi tiết một địa điểm.



Ví dụ:



```powershell

curl.exe "http://127.0.0.1:8001/admin/rag/place/KH\_0042"

```



Response mẫu:



```json

{

&nbsp; "found": true,

&nbsp; "place": {

&nbsp;   "place\_id": "KH\_0042",

&nbsp;   "name": "Dốc Lết",

&nbsp;   "province": "Khánh Hòa",

&nbsp;   "category\_main": "Thiên nhiên",

&nbsp;   "category\_sub": "Biển đảo/rừng núi/sinh thái"

&nbsp; }

}

```



---



\# 6. Place Search



\## GET `/admin/rag/places/search`



Dùng cho màn hình quản lý địa điểm.



Query params:



| Param | Ý nghĩa |

|---|---|

| `q` | từ khóa tìm kiếm |

| `province` | lọc tỉnh |

| `category` | lọc category |

| `active\_only` | chỉ lấy địa điểm active |

| `limit` | số kết quả |

| `min\_score` | ngưỡng điểm search |



Ví dụ:



```powershell

curl.exe "http://127.0.0.1:8001/admin/rag/places/search?q=doc%20let\&province=khanh\_hoa\&limit=10\&min\_score=30"

```



Response mẫu:



```json

{

&nbsp; "query": "doc let",

&nbsp; "province": "khanh\_hoa",

&nbsp; "count": 2,

&nbsp; "results": \[

&nbsp;   {

&nbsp;     "place\_id": "KH\_0042",

&nbsp;     "name": "Dốc Lết",

&nbsp;     "category\_main": "Thiên nhiên",

&nbsp;     "category\_sub": "Biển đảo/rừng núi/sinh thái",

&nbsp;     "search\_score": 135.0

&nbsp;   },

&nbsp;   {

&nbsp;     "place\_id": "KH\_0043",

&nbsp;     "name": "Bãi biển Dốc Lết",

&nbsp;     "category\_main": "Thiên nhiên",

&nbsp;     "category\_sub": "Biển đảo/rừng núi/sinh thái",

&nbsp;     "search\_score": 100.0

&nbsp;   }

&nbsp; ]

}

```



---



\# 7. RAG Retrieve Debug



\## POST `/admin/rag/retrieve-debug`



Dùng để debug truy xuất RAG.



Body:



```json

{

&nbsp; "message": "đi biển ở Khánh Hòa",

&nbsp; "top\_k": 6

}

```



PowerShell:



```powershell

@"

{

&nbsp; "message": "đi biển ở Khánh Hòa",

&nbsp; "top\_k": 6

}

"@ | Set-Content reports\\request\_rag\_debug\_khanhhoa.json -Encoding UTF8



curl.exe -X POST "http://127.0.0.1:8001/admin/rag/retrieve-debug" `

&nbsp; -H "Content-Type: application/json; charset=utf-8" `

&nbsp; --data-binary "@reports/request\_rag\_debug\_khanhhoa.json"

```



Response mẫu:



```json

{

&nbsp; "query": "đi biển ở Khánh Hòa",

&nbsp; "intent": {

&nbsp;   "province\_norm": "khanh\_hoa",

&nbsp;   "interests": \["beach"]

&nbsp; },

&nbsp; "debug": {

&nbsp;   "raw\_count": 120,

&nbsp;   "scored\_count": 120,

&nbsp;   "final\_count": 6

&nbsp; },

&nbsp; "results": \[

&nbsp;   {

&nbsp;     "place\_id": "KH\_0042",

&nbsp;     "title": "Dốc Lết",

&nbsp;     "category\_main": "Thiên nhiên",

&nbsp;     "category\_sub": "Biển đảo/rừng núi/sinh thái",

&nbsp;     "final\_score": 75.2106

&nbsp;   }

&nbsp; ]

}

```



---



\# 8. Simple Chat API



\## POST `/rag/chat/simple`



Dùng cho app/client gọi câu trả lời đơn giản.



Body:



```json

{

&nbsp; "message": "đi biển ở Khánh Hòa",

&nbsp; "top\_k": 6

}

```



PowerShell:



```powershell

@"

{

&nbsp; "message": "đi biển ở Khánh Hòa",

&nbsp; "top\_k": 6

}

"@ | Set-Content reports\\request\_chat\_simple\_khanhhoa.json -Encoding UTF8



curl.exe -X POST "http://127.0.0.1:8001/rag/chat/simple" `

&nbsp; -H "Content-Type: application/json; charset=utf-8" `

&nbsp; --data-binary "@reports/request\_chat\_simple\_khanhhoa.json"

```



Response mẫu:



```json

{

&nbsp; "answer": "Mình đã tìm được một số địa điểm phù hợp...",

&nbsp; "places": \[

&nbsp;   {

&nbsp;     "place\_id": "KH\_0042",

&nbsp;     "name": "Dốc Lết",

&nbsp;     "province": "Khánh Hòa",

&nbsp;     "category\_main": "Thiên nhiên",

&nbsp;     "category\_sub": "Biển đảo/rừng núi/sinh thái"

&nbsp;   }

&nbsp; ],

&nbsp; "model\_used": "retrieval\_template",

&nbsp; "runtime\_mode": "retrieval\_only"

}

```



---



\# 9. AI Logs



\## GET `/admin/ai/logs`



Dùng để xem request AI gần nhất.



Query params:



| Param | Ý nghĩa |

|---|---|

| `limit` | số log muốn lấy, tối đa 100 |



Ví dụ:



```powershell

curl.exe "http://127.0.0.1:8001/admin/ai/logs?limit=20"

```



Response mẫu:



```json

{

&nbsp; "total": 31,

&nbsp; "limit": 20,

&nbsp; "logs": \[

&nbsp;   {

&nbsp;     "query": "đi biển ở Khánh Hòa",

&nbsp;     "runtime\_mode": "retrieval\_only",

&nbsp;     "model\_used": "retrieval\_template",

&nbsp;     "fallback\_used": true,

&nbsp;     "latency\_ms": {

&nbsp;       "total": 33.04

&nbsp;     },

&nbsp;     "top\_place\_names": \[

&nbsp;       "Dốc Lết",

&nbsp;       "Bãi Tiên Nha Trang"

&nbsp;     ]

&nbsp;   }

&nbsp; ]

}

```



---



\# 10. AI Metrics



\## GET `/admin/ai/metrics`



Dùng để thống kê vận hành AI.



```powershell

curl.exe "http://127.0.0.1:8001/admin/ai/metrics"

```



Response mẫu:



```json

{

&nbsp; "total\_requests": 31,

&nbsp; "fallback\_count": 25,

&nbsp; "fallback\_rate": 0.8065,

&nbsp; "timeout\_count": 1,

&nbsp; "quota\_exceeded\_count": 12,

&nbsp; "cache\_hit\_count": 0,

&nbsp; "avg\_total\_latency": 2531.15,

&nbsp; "model\_usage": {

&nbsp;   "gemini-2.5-flash": 6,

&nbsp;   "template\_after\_gemini\_error": 16,

&nbsp;   "retrieval\_template": 9

&nbsp; }

}

```



---



\# 11. AI Debug Query



\## POST `/admin/ai/debug-query`



Dùng để chạy full pipeline và xem debug.



Body:



```json

{

&nbsp; "message": "đi Huế với bố mẹ lớn tuổi, ít đi bộ",

&nbsp; "mode": "balanced",

&nbsp; "top\_k": 6,

&nbsp; "include\_prompt": false

}

```



PowerShell:



```powershell

@"

{

&nbsp; "message": "đi Huế với bố mẹ lớn tuổi, ít đi bộ",

&nbsp; "mode": "balanced",

&nbsp; "top\_k": 6,

&nbsp; "include\_prompt": false

}

"@ | Set-Content reports\\request\_admin\_debug\_hue.json -Encoding UTF8



curl.exe -X POST "http://127.0.0.1:8001/admin/ai/debug-query" `

&nbsp; -H "Content-Type: application/json; charset=utf-8" `

&nbsp; --data-binary "@reports/request\_admin\_debug\_hue.json"

```



---



\# 12. Gemini Cache



\## GET `/admin/cache/status`



Dùng để xem cache Gemini.



```powershell

curl.exe "http://127.0.0.1:8001/admin/cache/status"

```



Response mẫu:



```json

{

&nbsp; "enabled": true,

&nbsp; "cache\_file": "data/cache/gemini\_response\_cache.jsonl",

&nbsp; "file\_exists": false,

&nbsp; "records\_in\_memory": 0,

&nbsp; "file\_size\_bytes": 0

}

```



\## POST `/admin/cache/clear`



Dùng để xóa cache Gemini.



```powershell

curl.exe -X POST "http://127.0.0.1:8001/admin/cache/clear"

```



Response mẫu:



```json

{

&nbsp; "cleared": true,

&nbsp; "old\_records": 0

}

```



---



\# 13. Data Quality Status



\## GET `/admin/data-quality/status`



Dùng để xem summary data quality.



```powershell

curl.exe "http://127.0.0.1:8001/admin/data-quality/status"

```



Response mẫu:



```json

{

&nbsp; "scan": {

&nbsp;   "place\_count": 5592,

&nbsp;   "issue\_count": 3315,

&nbsp;   "issue\_counts": {

&nbsp;     "category\_mismatch\_beach": 1029,

&nbsp;     "category\_mismatch\_nature": 1500,

&nbsp;     "category\_mismatch\_spiritual": 564,

&nbsp;     "coordinate\_out\_of\_vietnam\_range": 4,

&nbsp;     "possible\_duplicate\_name": 218

&nbsp;   }

&nbsp; },

&nbsp; "autofix": {

&nbsp;   "changed\_count": 153

&nbsp; },

&nbsp; "reviewed": {

&nbsp;   "exists": true

&nbsp; }

}

```



---



\# 14. Data Quality Issues



\## GET `/admin/data-quality/issues`



Dùng để xem danh sách lỗi data quality.



Query params:



| Param | Ý nghĩa |

|---|---|

| `issue\_type` | loại lỗi |

| `severity` | high / medium / low |

| `province` | lọc tỉnh |

| `q` | tìm theo tên/place\_id |

| `limit` | số dòng |

| `offset` | phân trang |



Ví dụ:



```powershell

curl.exe "http://127.0.0.1:8001/admin/data-quality/issues?province=Kh%C3%A1nh%20H%C3%B2a\&q=D%E1%BB%91c%20L%E1%BA%BFt\&limit=20"

```



Response mẫu:



```json

{

&nbsp; "total": 3,

&nbsp; "items": \[

&nbsp;   {

&nbsp;     "issue\_type": "category\_mismatch\_beach",

&nbsp;     "severity": "high",

&nbsp;     "place\_id": "KH\_0042",

&nbsp;     "name": "Dốc Lết"

&nbsp;   }

&nbsp; ]

}

```



---



\# 15. Data Quality Autofix Changes



\## GET `/admin/data-quality/autofix-changes`



Dùng để xem danh sách thay đổi auto-fix.



Query params:



| Param | Ý nghĩa |

|---|---|

| `province` | lọc tỉnh |

| `q` | tìm theo tên/place\_id |

| `limit` | số dòng |

| `offset` | phân trang |



Ví dụ:



```powershell

curl.exe "http://127.0.0.1:8001/admin/data-quality/autofix-changes?province=Kh%C3%A1nh%20H%C3%B2a\&q=D%E1%BB%91c%20L%E1%BA%BFt\&limit=20"

```



Response mẫu:



```json

{

&nbsp; "total": 1,

&nbsp; "items": \[

&nbsp;   {

&nbsp;     "place\_id": "KH\_0042",

&nbsp;     "name": "Dốc Lết",

&nbsp;     "old\_category\_main": "Di tích",

&nbsp;     "old\_category\_sub": "Điểm tham quan văn hóa",

&nbsp;     "new\_category\_main": "Thiên nhiên",

&nbsp;     "new\_category\_sub": "Biển đảo/rừng núi/sinh thái"

&nbsp;   }

&nbsp; ]

}

```



---



\# 16. Data Quality Summary By Province



\## GET `/admin/data-quality/summary-by-province`



Dùng để xem thống kê lỗi theo tỉnh.



```powershell

curl.exe "http://127.0.0.1:8001/admin/data-quality/summary-by-province"

```



Response mẫu:



```json

{

&nbsp; "total\_provinces": 63,

&nbsp; "items": \[

&nbsp;   {

&nbsp;     "province": "Khánh Hòa",

&nbsp;     "issue\_count": 55,

&nbsp;     "high\_count": 35,

&nbsp;     "medium\_count": 15,

&nbsp;     "low\_count": 5,

&nbsp;     "autofix\_count": 9

&nbsp;   }

&nbsp; ]

}

```



---



\# Recommended Dashboard Pages



\## 1. Overview



Endpoint:



```text

/admin/system/overview

/admin/system/self-test

```



Cards:



```text

\- Runtime Mode

\- RAG Ready

\- Using Reviewed Dataset

\- AI Requests

\- Fallback Rate

\- Data Quality Issues

\- Autofix Count

\- Cache Status

```



\## 2. RAG Debug



Endpoint:



```text

/admin/rag/retrieve-debug

/admin/rag/place/{place\_id}

```



Chức năng:



```text

\- Nhập query

\- Xem intent parser

\- Xem raw\_count/scored\_count/final\_count

\- Xem top places

\- Click place\_id để xem detail

```



\## 3. Place Management



Endpoint:



```text

/admin/rag/places/search

/admin/rag/place/{place\_id}

```



Chức năng:



```text

\- Search địa điểm

\- Filter province/category

\- Xem detail

```



\## 4. AI Monitoring



Endpoint:



```text

/admin/ai/logs

/admin/ai/metrics

/admin/ai/debug-query

```



Chức năng:



```text

\- Xem latency

\- Xem fallback

\- Xem model usage

\- Xem quota/timeout/cache hit

```



\## 5. Data Quality



Endpoint:



```text

/admin/data-quality/status

/admin/data-quality/issues

/admin/data-quality/autofix-changes

/admin/data-quality/summary-by-province

```



Chức năng:



```text

\- Xem số lỗi

\- Lọc lỗi theo tỉnh

\- Xem auto-fix

\- Biểu đồ issue theo province

```



---



\# Demo Checklist



Trước khi báo cáo:



```powershell

curl.exe "http://127.0.0.1:8001/admin/system/self-test"

```



Kỳ vọng:



```json

{

&nbsp; "ready": true,

&nbsp; "passed": 8,

&nbsp; "failed": 0

}

```



Chạy offline nhanh:



```env

AI\_RUNTIME\_MODE=retrieval\_only

ENABLE\_GEMINI=false

ENABLE\_LORA=false

ENABLE\_VALIDATOR=false

```



Demo Gemini:



```env

AI\_RUNTIME\_MODE=demo

ENABLE\_GEMINI=true

ENABLE\_LORA=false

ENABLE\_VALIDATOR=false

```



Nếu Gemini hết quota, hệ thống fallback template và vẫn trả địa điểm.

