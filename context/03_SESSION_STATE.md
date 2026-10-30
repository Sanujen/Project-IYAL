# Project IYAL — AI Agent Session State

## Current Version: `v2.0.0` (Monolithic Overhaul Complete)
**Last Updated**: 2026-10-31

---

## Phase Completion Tracker

- [x] **Phase 1: Repository Audit, Cleanup & `context/` Knowledge Base**
  - Removed unused directories: `error_analyzis/`, `iyal_quality_analyzer/error_analyzis/`, `training/`, `imgs/`, `docs/build/`, `feedback/`, `ui/`.
  - Created `context/` directory with project overview, ADRs, API/DB schema, session state, and Phase 5 add-ons roadmap.
- [x] **Phase 2: Core NLP & Normalization Engine (`iyal_quality_analyzer`) Refactoring**
  - Fixed `english_word_check.py` (cached NLTK corpus, removed Bamini syllable collisions, added UI/DB Protected Corpus support).
  - Fixed `legacy_converter.py` (precomputed unique/common character sets, fixed Bamini `;` pulli detection bug, normalized escaped keys).
  - Replaced broken `googletrans==3.1.0a0` / `httpx==0.13.3` with fast `@lru_cache` + `requests.Session()` implementations in `transliteration.py` and `translator.py`.
  - Upgraded `inference.py` (Classifier) and `inference_coll_to_stand.py` (mBART Standardizer) to check local HuggingFace cache first and support runtime switching between `default` (local venv) and `custom` (hosted HTTP URL or custom HF repo).
- [x] **Phase 3: Monolithic FastAPI Backend (`server/`)**
  - Built zero-cost SQLite WAL database (`server/database.py`, `server/models_db.py`) with optional `DATABASE_URL` PostgreSQL support.
  - Built Hybrid Gmail/Google OAuth2 + PBKDF2/JWT Authentication & RBAC (`superadmin` vs `admin`) in `server/auth.py`.
  - Built In-Monolith DDoS Rate Limiter, Auto-IP Ban, Brute-Force Lockout, and Payload/Concurrency Guards in `server/security.py`.
  - Built Dynamic Dual-Model Manager in `server/model_manager.py`.
- [x] **Phase 4: Frontend SPA (`/` and `/admin`), Containerization, Docs & End-to-End Verification**
  - Built Public Normalizer SPA (`server/static/index.html`, `js/app.js`) implementing all 11 pipeline steps, legacy font confirmation banner, protected words editor, file upload/export, and feedback modal.
  - Built Admin Portal (`server/static/admin.html`, `js/admin.js`) with Feedback triage, Dual-Model hot-swap & live tester, Superadmin Gmail user invitation & RBAC, Protected Corpus manager, and Observability/Security dashboard.
  - Updated `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `setup.py`, `.env.example`, `README.md`, and `docs/IMPLEMENTATION_REPORT.md`.
  - Verified all 7 end-to-end test suites in `tests/test_all.py`.
- [ ] **Phase 5: Recommended High-Value Add-Ons (Future Roadmap — Intentionally Not Implemented Initially)**
  - See `context/04_RECOMMENDED_ADDONS.md` for detailed specifications (Active Learning feedback export, Browser Extension, ONNX INT8 quantization & offline transliteration fallback, OCR PDF support, and Batch Dialect Analytics).

