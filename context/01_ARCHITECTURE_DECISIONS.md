# Architecture Decisions (ADRs)

## ADR-01: Single Monolithic Server (FastAPI + Embedded SPA Frontend)
- **Context**: Previously, the project ran three separate services (`FastAPI` on port 8000, `Streamlit` UI on port 8501, and `Sphinx` nginx docs on port 80) plus an external PostgreSQL server. Streamlit made it impossible to properly serve a dedicated `/admin` URL route with RBAC, JWT/OAuth2 authentication, rate limiting, and fine-grained interactive legacy font confirmation.
- **Decision**: Consolidate the entire application into a **single monolithic FastAPI server**:
  - Serves the public web application at `/`
  - Serves the protected Admin Portal at `/admin`
  - Serves REST APIs under `/api/v1/*` and maintains 100% backward compatibility with legacy endpoints (`/analyze/`, `/legacy2unicode/`, `/get_encoding/`, `/colloquial_to_standard/`, `/feedback/`).
- **Benefits**: Single port, zero inter-container latency, unified DDoS/rate-limiting middleware, lower RAM usage on the university server, and effortless deployment via a single container in `docker-compose.yml`.

## ADR-02: Zero-Cost Database (SQLite WAL by Default + Optional PostgreSQL)
- **Context**: The application is hosted on a university-provided server and must be 100% cost-free with no paid cloud database dependencies.
- **Decision**: Use **SQLAlchemy 2.0** backed by an embedded **SQLite database in WAL (Write-Ahead Logging) mode** (`data/iyal.db`) by default, while allowing seamless override via `DATABASE_URL` (e.g., PostgreSQL) if configured.
- **Benefits**: Zero cost, zero external daemon overhead, ACID compliant, concurrent reads in WAL mode, persisted via Docker volume.

## ADR-03: Hybrid Admin Authentication (Predefined Superadmin + Gmail Invite & Google OAuth2 / Password)
- **Context**: `/admin` must be protected by a predefined `superadmin` user who can invite other `admin` users via Gmail. Only `superadmin` can manage admin accounts.
- **Justification for Hybrid Auth (Google OAuth2 + Gmail Invite Password/Token)**:
  - Pure Google OAuth2 requires a public registered top-level domain in Google Cloud Console and **rejects raw IP addresses** (which university servers frequently use prior to DNS setup).
  - Therefore, we implement a **Hybrid Gmail-First Authentication System**:
    1. **Predefined Superadmin**: Seeded automatically on startup from environment variables (`SUPERADMIN_EMAIL`, `SUPERADMIN_USERNAME`, `SUPERADMIN_PASSWORD`).
    2. **Gmail Invitation Flow**: Superadmin invites admins by their `@gmail.com` (or institutional) email address.
    3. **Dual Sign-In**:
       - **Google Sign-In (OAuth2 ID Token Verification)**: When `GOOGLE_CLIENT_ID` is set, invited Gmail users click "Sign in with Google", and the backend cryptographically verifies the Google ID token and matches the email against active/invited admins.
       - **Email + Password / Invite Code**: Invited Gmail users can also activate their account using their invite token/temporary password and sign in directly with Email + Password (works on localhost, LAN IPs, and raw university server IPs with zero external OAuth setup).

## ADR-04: Dynamic Dual-Model Management (Default Local Venv vs. Custom Hosted URL / HF Repo)
- **Context**: We have two ML models:
  1. Legacy vs. Romanized Classifier (`sanujen/Tamil_Legacy_Roman_Classifier_V2` / `sanujen/fyp_0`)
  2. Colloquial-to-Standard Tamil Standardizer (`sanujen/mBART_Tamil_Colloquial_to_Standard`)
  Admins need the ability to switch each model independently between `default` (local Python venv/HuggingFace cache model) and `custom` (a custom hosted HTTP endpoint URL or a custom HuggingFace repository URL/ID).
- **Decision**: Implement a thread-safe `ModelManager` singleton that persists model configuration in the database (`model_configs` table) and supports:
  - `mode = "default"`: Uses the local cached HuggingFace model inside the Python environment (checking local HF cache first to avoid unnecessary downloads).
  - `mode = "custom"`:
    - If `custom_url` is an HTTP REST inference endpoint (or HuggingFace Inference API URL), sends JSON payloads (`{"inputs": text}` / `{"input_text": text}`) with optional Bearer auth header and parses predictions.
    - If `custom_url` is a `huggingface.co/<org>/<repo>` URL or `<org>/<repo>` identifier, loads that model via `transformers`.

## ADR-05: In-Monolith DDoS, Brute-Force & Resource Protection
- **Context**: Since there is no external WAF or API gateway in front of the university server, all protection must live inside the monolithic server.
- **Decision**:
  1. **Sliding-Window IP Rate Limiter & Auto-Ban**: Per-IP rate limiting across 3 tiers (`general`, `inference`, `auth`), with automatic temporary IP ban upon repeated violations.
  2. **Brute-Force Login Lockout**: Tracks failed login attempts per IP and per account; locks out after 5 failed attempts for 15 minutes and records a security audit event.
  3. **Concurrency Semaphore & Payload Limits**: Limits max request body size (5 MB), max text input length (15,000 chars default), and concurrent heavy ML inference executions via `asyncio.Semaphore` / thread lock to prevent CPU/RAM exhaustion.
  4. **Security Headers**: Adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `X-Request-ID` tracing headers to every response.

