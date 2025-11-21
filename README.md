# TiepLM - Trợ Lý AI cho Khoá Học CS431

Trợ lý AI kiểu NotebookLM cho nội dung video khoá học CS431 Deep Learning.

## Trạng Thái: ✅ Hoàn Thành

Đã triển khai và đánh giá đầy đủ 4 tính năng AI:
- **Tóm tắt văn bản**: Tóm tắt phân cấp với trích dẫn inline
- **Hỏi đáp**: Trả lời câu hỏi với nguồn trích dẫn
- **Tóm tắt video**: Tóm tắt theo timestamp
- **Sinh câu hỏi**: Tạo câu hỏi trắc nghiệm và tự luận

Hệ thống sử dụng **RAG** với hybrid search (Vector + BM25), cross-encoder reranking, và contextual retrieval.

## Kiến Trúc

- **Backend**: FastAPI (modular monolith)
- **Frontend**: React TypeScript
- **Databases**: PostgreSQL (metadata) + Qdrant (vector embeddings)
- **Ingestion**: Pipeline độc lập với contextual retrieval

## Cài Đặt Nhanh

```bash
# 1. Cấu hình môi trường
cp .env.example .env
# Sửa .env: Thêm OPENAI_API_KEY

# 2. Cài đặt dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Khởi động databases
docker-compose up -d

# 4. Khôi phục dữ liệu (đọc chi tiết ở README_en.md)
# Option A: Từ exports (khuyên dùng)
docker exec -i tieplm-postgres psql -U tieplm -d tieplm < tieplm_db_dump.sql
cd backend && alembic upgrade head && cd ..
curl -X POST 'http://localhost:6333/collections/cs431_course_transcripts/snapshots/upload' -F 'snapshot=@qdrant_snapshot.snapshot'

# Option B: Chạy pipeline đầy đủ (xem ingestion/README.md)

# 5. Chạy ứng dụng
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm install && npm start
```

**API Docs:** http://localhost:8000/docs
**Frontend:** http://localhost:3000

## Stack Công Nghệ

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Frontend**: React 18, TypeScript, Vite, Chakra UI v2, Zustand, TanStack React Query
- **Databases**: PostgreSQL, Qdrant
- **RAG**: Hybrid search (Vector + BM25), Cross-encoder reranking
- **LLM**: OpenAI gpt-5-mini
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Transcription**: OpenAI Whisper large-v3 (local)

## Tài Liệu

Đọc thêm ở file **[README_en.md](./README_en.md)** cho hướng dẫn chi tiết về:
- Kiến trúc hệ thống và cấu hình
- Chi tiết ingestion pipeline
- Module backend và frontend
- Framework đánh giá và kết quả

Tài liệu khác:
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - Thiết kế kiến trúc
- [`evaluation/README.md`](./evaluation/README.md) - Đánh giá và kết quả
- [`ingestion/README.md`](./ingestion/README.md) - Pipeline xử lý dữ liệu
- [`backend/README.md`](./backend/README.md) - Module backend
- [`frontend/README.md`](./frontend/README.md) - Giao diện frontend

## Thành Viên

- **Giảng Viên:** TS. Nguyễn Vinh Tiệp (tiepnv@uit.edu.vn)
- **Sinh Viên:**
    - Nguyễn Thuận Phát (23521146@gm.uit.edu.vn)
    - Phan Thuỷ Phương (23521248@gm.uit.edu.vn)
    - Nguyễn Phong Huy (23520637@gm.uit.edu.vn)
    - Đào Mạnh Dũng (23520325@gm.uit.edu.vn)

## Demo

## Demo

<a href="https://drive.google.com/file/d/1GldmcmE8LBmEC79EtdvKssLF7zh9herr/view">
  <img src="https://drive.google.com/thumbnail?id=1GldmcmE8LBmEC79EtdvKssLF7zh9herr" width="800" />
</a>

