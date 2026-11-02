# இயல் (Project IYAL) — Tamil Input Text Normalizer & Standardizer (v2.0)

**Project IYAL** is a unified, lightweight, high-performance monolithic web application and Python NLP library that normalizes heterogeneous Tamil text inputs—combining **Raw Tamil Unicode**, **Mixed Tamil+English Unicode**, **Romanized Tanglish**, **25 Legacy Tamil Font Encodings (Bamini, Anjal, TSCII, TAB, TAM, Vanavil, etc.)**, and **English words**—into clean, standardized **Tamil Unicode**.

---

## 🌟 Key Highlights in v2.0

1. **Unified Monolithic Server (`FastAPI` + Embedded SPA Frontend + `SQLite WAL`)**:
   - Serves the Public Normalization App at `/`, the RBAC-protected Admin Portal at `/admin`, and the REST API at `/api/v1/*` (plus 100% backward compatibility with legacy routes `/analyze/`, `/get_encoding/`, `/legacy2unicode/`, `/colloquial_to_standard/`, `/feedback/`) from a **single process and port**.
   - Uses a zero-cost embedded **SQLite (WAL Mode)** database (`./data/iyal.db`) out of the box—perfect for university server hosting with zero cloud database bills—while supporting seamless PostgreSQL override via `DATABASE_URL`.
2. **Complete 11-Step Normalization Pipeline**:
   - **Step 1**: Input multi-sentence paragraphs or upload `.docx`, `.txt`, and `.pdf` documents.
   - **Step 2**: Sentence & token segmentation (preserving URLs, emails, phone numbers, and bracketed expressions).
   - **Steps 3 & 4**: 5-type token classification (`Raw Tamil Unicode`, `Mixed Tamil+English`, `English / Protected Corpus`, `Legacy Font Encoding`, `Romanized Tanglish`).
   - **Step 5**: $O(1)$ cached NLTK English vocabulary lookup + **User-Configurable Protected Words** via the UI (words that must never be transliterated or translated).
   - **Step 6**: Fine-tuned BERT sequence classifier (`sanujen/Tamil_Legacy_Roman_Classifier_V2` / `sanujen/fyp_0`) to distinguish Legacy Font tokens from Romanized Tanglish tokens.
   - **Step 7**: Automatic Legacy Font identification (`encode2unicode` across 25 Tamil legacy fonts) with an **interactive UI Confirmation Banner** showing live Tamil Unicode previews before converting.
   - **Step 8**: Fast, LRU-cached Tamil transliteration for Romanized Tanglish words.
   - **Step 9**: Sentence and paragraph restructuring with original punctuation.
   - **Step 10**: Optional phrase-level English-to-Tamil translation (`need_translation`), automatically preserving user-protected words.
   - **Step 11**: Optional Colloquial-to-Standard Tamil standardization (`colloquial_to_standard`) powered by our fine-tuned mBART model (`sanujen/mBART_Tamil_Colloquial_to_Standard`).
3. **Public Feedback & Protected `/admin` Portal**:
   - Users can submit categorized, rated feedback with full input/output context in one click.
   - `/admin` is protected by a predefined **Superadmin** account and supports **Hybrid Gmail Authentication** (both Google OAuth 2.0 Sign-In and Gmail Invitation Tokens / Password login).
   - **Role-Based Access Control (RBAC)**:
     - `superadmin`: Full access + **Admin User Management** (invite admins by Gmail, activate/deactivate, delete).
     - `admin`: Access to Feedback triage, Model Management, Protected Corpus, and Observability logs (cannot manage other admin users).
4. **Dynamic Dual-Model Management**:
   - Admins can switch either Model 1 (`classifier`) or Model 2 (`standardizer`) at runtime between:
     - **`default`**: Local model inside the Python environment / HuggingFace cache.
     - **`custom`**: Any custom hosted HTTP inference endpoint URL or custom HuggingFace repository URL (with optional Bearer API key) and test it live from `/admin`.
5. **In-Monolith DDoS, Brute-Force & Observability Engine**:
   - Sliding-window IP rate limiting across route tiers (`general`, `inference`, `feedback`) with automatic temporary IP bans for repeated violations.
   - Brute-force login protection (locks out IP/account after 5 failed attempts for 15 minutes).
   - Request payload size guards, ML inference concurrency semaphores, `X-Request-ID` tracing, rotating log files (`logs/app.log`, `logs/error.log`), and a live log/security dashboard in `/admin`.

---

## 📁 Repository Structure

```text
Project-IYAL/
├── context/                        # Persistent AI Agent context & session state
│   ├── 00_PROJECT_OVERVIEW.md      # 11-step domain flow & system overview
│   ├── 01_ARCHITECTURE_DECISIONS.md# Monolith, SQLite WAL, Hybrid Gmail Auth, DDoS ADRs
│   ├── 02_API_AND_DATA_SCHEMA.md   # Database tables & REST API specifications
│   ├── 03_SESSION_STATE.md         # Phase-by-phase progress & verification state
│   └── 04_RECOMMENDED_ADDONS.md    # Phase 5 future high-value add-ons roadmap
├── iyal_quality_analyzer/          # Core Python NLP Package (pip-installable)
│   ├── __init__.py
│   ├── quality_analyzer.py         # 11-step normalization pipeline
│   ├── inference_base/
│   │   ├── inference.py            # Model 1: Legacy vs. Romanized Classifier
│   │   └── inference_coll_to_stand.py # Model 2: Colloquial-to-Standard mBART
│   └── utils/
│       ├── unicode_classifier.py   # Unicode range categorization
│       ├── english_word_check.py   # Cached NLTK corpus + custom protected words
│       ├── special_case_check.py   # URL, email, phone, bracket detection
│       ├── transliteration.py      # Cached Google Input Tools Tamil transliterator
│       ├── translator.py           # Cached English-to-Tamil translator
│       ├── legacy_converter/       # 25 legacy Tamil font charmaps & auto-detector
│       └── logger/                 # Rotating file + ring-buffer structured logger
├── server/                         # Monolithic FastAPI Server + Static Web UI
│   ├── server.py                   # FastAPI application entrypoint
│   ├── config.py                   # Environment settings
│   ├── database.py                 # SQLAlchemy 2.0 + SQLite WAL / PostgreSQL engine
│   ├── models_db.py                # ORM models (AdminUser, Feedback, ModelConfig, etc.)
│   ├── auth.py                     # PBKDF2, JWT, Google OAuth2 & RBAC dependencies
│   ├── security.py                 # DDoS rate limiter, IP auto-ban & brute-force guard
│   ├── retention.py                # Server retention policy engine & SQLite VACUUM
│   ├── model_manager.py            # Runtime dual-model manager (default vs. custom URL)
│   ├── file_parser.py              # .docx, .txt, .pdf text extraction & .docx export
│   └── static/                     # Frontend SPA for `/` and `/admin`
├── docs/                           # Architecture & Implementation Report with Mermaid diagrams
├── tests/                          # End-to-end automated test suite
├── .env.example                    # Template environment configuration
├── Dockerfile                      # Production CPU-optimized Docker image
├── docker-compose.yml              # Single-command deployment with persistent volumes
├── requirements.txt                # Clean, conflict-free Python dependencies
└── setup.py                        # Package installer for `iyal_quality_analyzer`
```

---

## 🚀 Quick Start (Local Development)

### 1. Clone & Set Up Virtual Environment
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure `.env`
Copy `.env.example` to `.env` and customize if needed:
```bash
cp .env.example .env
```
Default predefined Superadmin credentials (override in `.env` for production):
- **Username**: `superadmin` (or `superadmin@gmail.com`)
- **Password**: `IyalAdmin@2026`

### 3. Run the Monolithic Server
```bash
uvicorn server.server:app --host 0.0.0.0 --port 8000 --reload
```
- **Public Normalizer Web App**: `http://localhost:8000/`
- **Protected Admin Portal**: `http://localhost:8000/admin`
- **Interactive OpenAPI Docs**: `http://localhost:8000/api/docs`

---

## 🐳 Docker Compose & Docker Hub Deployment (University Server Ready)

### Option A: Pull Pre-Built Public Image from Docker Hub
Anyone can pull and run the official public Docker image directly from Docker Hub (`sathveegan/project-iyal:latest`):

```bash
docker pull sathveegan/project-iyal:latest
cp .env.example .env
docker compose up -d
```

### Option B: Build & Run Locally with Docker Compose
Deploy the entire stack with persistent volumes for the SQLite database (`./data`), logs (`./logs`), and HuggingFace model cache (`./model_cache`):

```bash
cp .env.example .env
docker compose up -d --build
```

To view logs or stop:
```bash
docker compose logs -f
docker compose down
```

> **Tip**: Set `RESEARCHGATE_PAPER_URL` in `.env` to customize the target link of the **📄 ResearchGate Paper** button in the web UI.

---

## 📦 Using `iyal_quality_analyzer` as a Python Library

```python
from iyal_quality_analyzer import (
    Inference,
    CollToStandInference,
    detect_legacy_encoding_details,
    multi_sentence_quality_analyzer,
    convert_legacy_to_unicode,
)

classifier = Inference()
standardizer = CollToStandInference()

text = "Kaalai வணkkam உலகம் cyfk; Moratuwa."

# Step 6 & 7: Detect Legacy Font & get preview samples
enc_info = detect_legacy_encoding_details(
    classifier, text, protected_words=["Moratuwa"]
)
print(enc_info)
# {'encoding': 'bamini2utf8', 'requires_confirmation': True, 'legacy_samples': [{'word': 'cyfk;', 'preview_unicode': 'உலகம்'}]}

# Full 11-Step Normalization
normalized_text, details = multi_sentence_quality_analyzer(
    classifier=classifier,
    coll_to_stand=standardizer,
    input_text=text,
    encoding=enc_info["encoding"],
    need_translation=False,
    colloquial_to_standard=False,
    protected_words=["Moratuwa"],
)
print(normalized_text)
# காலை வணக்கம் உலகம் உலகம் Moratuwa.
```

---

---

## 💾 Storage Capacity & Data Retention Policy

When self-hosting on a server or Docker container, Project IYAL provides an automated, zero-cost retention engine to prevent disk space exhaustion (`ENOSPC`):

- **Server-Level Defaults (`.env`)**:
  - `RETENTION_AUDIT_LOG_DAYS=30`: Automatically purges audit logs older than 30 days.
  - `RETENTION_FEEDBACK_RESOLVED_DAYS=90`: Automatically purges resolved/reviewed feedback older than 90 days (`new` feedback is never deleted).
  - `RETENTION_CLEANUP_INTERVAL_HOURS=24`: Periodic background task executes cleanup daily.
  - `RETENTION_AUTO_VACUUM=true`: Automatically executes SQLite WAL checkpoint and `VACUUM` to release freed pages back to the filesystem.
  - `LOG_ROTATION_MAX_BYTES=5242880` & `LOG_ROTATION_BACKUP_COUNT=3`: Limits log file size to 5 MB per file with up to 3 rotated backups.
- **Admin Portal UI (`/admin`)**:
  - Displays real-time host disk capacity (Free / Total GB), SQLite DB size (Main, WAL, Freelist estimate), and log directory size.
  - Allows administrators to dynamically update retention periods and schedules at runtime without restarting the server.
  - Provides a one-click **"🧹 Run Cleanup Now"** button for immediate manual cleanup and disk space reclamation.

## 🧪 Running Automated Tests

```bash
python tests/test_all.py
```
