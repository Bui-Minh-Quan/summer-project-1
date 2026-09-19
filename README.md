# 📈 Financial AI Platform - VN30 Quantitative Engine

![Project Banner](home.png)  


## 1. Mô tả dự án

**Financial Event Reasoning System** là hệ thống phân tích và dự báo xu hướng thị trường chứng khoán dựa trên sự kết hợp giữa Mô hình Ngôn ngữ Lớn (LLM) và Đồ thị Tri thức Thời gian (Temporal Knowledge Graph).

Dự án được truyền cảm hứng và kế thừa phương pháp luận từ nghiên cứu [*“Temporal Relational Reasoning of Large Language Models for Detecting Stock Portfolio Crashes”* (arXiv:2410.17266)](https://arxiv.org/pdf/2410.17266?utm_source=gemini). Tuy nhiên, thay vì tập trung vào bài toán cảnh báo sụp đổ danh mục (portfolio crash detection) như nguyên bản của bài báo, hệ thống được tinh chỉnh và mở rộng để phục vụ hai mục tiêu chính:

1. **Dự báo xu hướng (Trend Prediction):** Phân tích sự lan truyền tác động của các sự kiện tài chính qua không gian thời gian để hỗ trợ dự báo xu hướng biến động của tài sản.
2. **Lập luận giải thích (Event-based Reasoning):** Khai thác khả năng suy luận của LLM để tự động tổng hợp các chuỗi quan hệ nhân quả, cung cấp cơ sở giải thích minh bạch cho các biến động thị trường dựa trên dữ liệu tin tức và giao dịch thực tế.

Được thiết kế theo kiến trúc **Event-Driven Microservices**, hệ thống tích hợp luồng dữ liệu thời gian thực thông qua **Apache Kafka**, xử lý tự động hàng chục nghìn bản tin tài chính bằng **vLLM** (tối ưu với continuous batching), xây dựng đồ thị quan hệ bằng **Neo4j**, và cung cấp tầng phục vụ real-time qua **FastAPI** kết hợp **WebSockets** và **Redis**.

---

## 2. Tính năng nổi bật

* **Suy luận Đồ thị Tri thức (Knowledge Graph & TRR):** Tự động đọc hiểu báo cáo tài chính (PDF/TXT), trích xuất các thực thể và mối quan hệ tác động (Positive/Negative/Neutral), lưu trữ vào **Neo4j**. Sử dụng vLLM để đưa ra lý giải logic về xu hướng cổ phiếu.
* **Dự phóng Giá Đa khung thời gian (Multi-Horizon Regression):** Mô hình **XGBoost** dự báo tỷ suất sinh lời và mức giá kỳ vọng cho các phiên giao dịch tiếp theo (T+1 đến T+5).
* **Xử lý Dữ liệu Thời gian thực (Real-time Streaming):** Tích hợp dữ liệu thị trường (VNStock) và mạng xã hội (FireAnt) qua **Apache Kafka**, truyền tới Frontend qua **WebSocket**.
* **Chỉ số Tâm lý Đám đông (Social Hype Index):** Lượng hóa cảm xúc và mức độ tương tác (Likes, Shares, Comments) từ cộng đồng để phát hiện sự phân kỳ giữa tâm lý và giá cả.
* **Kiểm định & Đánh giá tự động (Backtest Audit Logs):** Tự động lưu vết các dự báo (Classification & Regression) và đối chiếu với kết quả thực tế của thị trường (T+1) để đánh giá độ chính xác của mô hình.

---

## 3. Công nghệ sử dụng (Tech Stack)

* **Frontend:** React 19, Vite, Tailwind CSS, `@xyflow/react` (vẽ Graph), Recharts, Lucide Icons.
* **Backend / API Gateway:** FastAPI, Python 3.12, AsyncIO, Uvicorn.
* **AI & Machine Learning:** vLLM (Qwen-1.5b), XGBoost, MLflow (MLOps Model Tracking).
* **Data Pipeline & Streaming:** Apache Kafka, Confluent Kafka Python.
* **Databases:**
  * **MongoDB:** Lưu trữ dữ liệu thô và dữ liệu đã xử lý.
  * **Neo4j:** CSDL Đồ thị lưu trữ đồ thị tri thức (Knowledge Graph).
  * **Redis:** Caching cho các truy vấn AI và Session.
* **DevOps & Infrastructure:** Docker, Docker Compose, Nginx.

---

## 4. Demo Hệ thống

* **Link Video Demo Hệ thống:** [Xem Video Demo trên Google Drive](https://drive.google.com/file/d/1Eep7WAoS-I6KL-TrVYUpIoCxZytNIWDY/view?usp=sharing)

![Dashboard Screenshot](dashboard.png)  

![Knowledge Graph Screenshot](graph_extractor.png)  

---

## 5. Hướng dẫn cài đặt 

### Yêu cầu hệ thống:
* Docker & Docker Compose
* GPU hỗ trợ CUDA (nếu chạy vLLM Engine ở local) hoặc endpoint vLLM tương thích.

### Các bước triển khai:

**Bước 1: Clone repository**
```bash
git clone https://github.com/your-username/financial-ai-platform.git
cd financial-ai-platform
```

**Bước 2: Cấu hình biến môi trường**  
Tạo file `.env` từ file mẫu `.env.example` và điền các thông số kết nối:
```bash
cp .env.example .env
```

**Bước 3: Khởi chạy toàn bộ hệ thống bằng Docker Compose**  
Lệnh này sẽ tự động build và chạy Frontend, API Gateway, các Microservices cùng hệ sinh thái Database (MongoDB, Neo4j, Redis, Kafka):
```bash
docker compose up -d --build
```

**Bước 4: Truy cập ứng dụng**  
* **Web App (Frontend):** `http://localhost`
* **API Gateway Documentation (Swagger):** `http://localhost:8000/docs`

---

## 📂 6. Cấu trúc Dự án

```text
financial-ai-platform/
├── app/                        # User-facing Applications
│   ├── api/                    # FastAPI Gateway (Routing, Auth, Caching)
│   └── web/                    # React + Vite Frontend (UI, React Flow, WebSockets)
├── modules/                    # Event-driven Backend Microservices
│   ├── acquisition/            # Thu thập dữ liệu VNStock & FireAnt -> Đẩy vào Kafka
│   ├── extraction/             # NLP Engine: Lọc tin tức, tạo Feature Vector & Graph Relations
│   ├── graph/                  # Graph Engine: Canonicalize và ghi dữ liệu vào Neo4j (Cypher)
│   ├── mlops/                  # MLOps: Quản lý vòng đời Model XGBoost (Train, Evaluate, MLflow)
│   └── reasoning/              # Reasoning Engine: Truy vấn Neo4j & gọi vLLM để suy luận chuỗi
├── docker-compose.yml          # Cấu hình triển khai hệ thống lõi
└── docker-compose.llm.yml      # Cấu hình triển khai LLM Engine (vLLM GPU)
```
