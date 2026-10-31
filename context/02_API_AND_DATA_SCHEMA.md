# API & Database Schema Reference

## 1. Database Schema (`server/models_db.py`)

### `admin_users`
| Column | Type | Description |
|---|---|---|
| `id` | `Integer` (PK) | Auto-increment ID |
| `email` | `String(255)` (Unique) | Admin Gmail / email address |
| `username` | `String(100)` (Unique) | Username |
| `password_hash` | `String(255)` | PBKDF2-HMAC-SHA256 salted password hash |
| `role` | `String(30)` | `"superadmin"` or `"admin"` |
| `is_active` | `Boolean` | Whether account is active |
| `invite_token` | `String(128)` (Nullable) | One-time invite token for invited Gmail users |
| `invited_by` | `String(255)` (Nullable) | Email of the superadmin who invited this user |
| `created_at` | `DateTime` | Creation timestamp (UTC) |
| `last_login_at` | `DateTime` (Nullable) | Last login timestamp |

### `feedback`
| Column | Type | Description |
|---|---|---|
| `id` | `Integer` (PK) | Auto-increment ID |
| `created_at` | `DateTime` | Timestamp |
| `category` | `String(64)` | e.g., `"general"`, `"classification"`, `"legacy_conversion"`, `"transliteration"`, `"standardization"` |
| `rating` | `Integer` (Nullable) | 1–5 user rating |
| `input_text` | `Text` (Nullable) | Original input text |
| `output` | `JSON` | Normalization output & token classification details |
| `feedback` | `Text` | User feedback message |
| `status` | `String(32)` | `"new"`, `"reviewed"`, `"resolved"` |
| `admin_notes` | `Text` (Nullable) | Notes added by admin |
| `client_ip` | `String(64)` (Nullable) | Submitter IP (for abuse tracking) |

### `model_configs`
| Column | Type | Description |
|---|---|---|
| `id` | `Integer` (PK) | Auto-increment ID |
| `model_key` | `String(64)` (Unique) | `"classifier"` or `"standardizer"` |
| `mode` | `String(32)` | `"default"` or `"custom"` |
| `default_model_name` | `String(255)` | Default HuggingFace model repo |
| `custom_url` | `String(512)` (Nullable) | Custom hosted model URL or HF repo |
| `api_key` | `String(512)` (Nullable) | Optional Bearer token for custom hosted URL |
| `updated_by` | `String(255)` (Nullable) | Admin who last updated config |
| `updated_at` | `DateTime` | Last update timestamp |

### `protected_words`
| Column | Type | Description |
|---|---|---|
| `id` | `Integer` (PK) | Auto-increment ID |
| `word` | `String(128)` (Unique) | Lowercase English / proper noun word to never transliterate |
| `skip_translation` | `Boolean` | If True, also skip translating this word when `need_translation=True` |
| `added_by` | `String(255)` | `"user"` or admin email |
| `created_at` | `DateTime` | Timestamp |

### `audit_logs`
| Column | Type | Description |
|---|---|---|
| `id` | `Integer` (PK) | Auto-increment ID |
| `timestamp` | `DateTime` | UTC timestamp |
| `level` | `String(20)` | `"INFO"`, `"WARNING"`, `"ERROR"`, `"SECURITY"` |
| `event_type` | `String(64)` | e.g., `"auth_login"`, `"auth_failed"`, `"model_update"`, `"rate_limit"`, `"pipeline_error"` |
| `actor` | `String(255)` | User email or IP |
| `details` | `Text` | JSON or descriptive details |

---

## 2. REST API Endpoints

### Public Normalization & Utility Endpoints
- `POST /api/v1/analyze` (and legacy `POST /analyze/`)
  - Body: `{"input_text": str, "encoding": Optional[str], "need_translation": bool, "colloquial_to_standard": bool, "protected_words": Optional[List[str]]}`
  - Returns: `{"output": str, "result": list, "detected_encoding": Optional[str], "metrics": dict}`
- `POST /api/v1/detect-encoding` (and legacy `POST /get_encoding/`)
  - Body: `{"input_text": str, "protected_words": Optional[List[str]]}`
  - Returns: `{"encoding": str, "legacy_samples": list, "requires_confirmation": bool}`
- `POST /api/v1/legacy2unicode` (and legacy `POST /legacy2unicode/`)
  - Body: `{"input_text": str, "encoding": Optional[str]}`
- `POST /api/v1/colloquial-to-standard` (and legacy `POST /colloquial_to_standard/`)
  - Body: `{"input_text": str}`
- `POST /api/v1/upload-extract`
  - Multipart file upload (`.txt`, `.docx`, `.pdf`) -> returns extracted text.
- `POST /api/v1/export-docx`
  - Body: `{"text": str}` -> returns `.docx` binary stream.
- `GET /api/v1/protected-words`
  - Lists globally configured protected corpus words.
- `POST /api/v1/feedback` (and legacy `POST /feedback/`)
  - Submits user feedback with rate-limit protection.
- `GET /api/v1/public-config`
  - Returns public UI configuration (`project_name`, `version`, `researchgate_paper_url` configured via `RESEARCHGATE_PAPER_URL` in `.env`).
- `GET /api/v1/health`
  - Returns server health, database status, model status, `researchgate_paper_url`, and uptime.

### Admin & Authentication Endpoints (`/api/v1/admin/*` & `/api/v1/auth/*`)
- `POST /api/v1/auth/login` — Email/Username + Password login (with brute-force protection).
- `POST /api/v1/auth/google` — Google OAuth2 ID Token login for invited Gmail admins.
- `POST /api/v1/auth/accept-invite` — Set password using invite token for invited Gmail admin.
- `GET /api/v1/auth/me` — Current authenticated admin profile.
- `GET /api/v1/admin/feedback` — Paginated/filtered list of user feedback.
- `PATCH /api/v1/admin/feedback/{id}` — Update feedback status (`new`, `reviewed`, `resolved`) & admin notes.
- `DELETE /api/v1/admin/feedback/{id}` — Delete feedback entry.
- `GET /api/v1/admin/models` — Get status & config of both models (`classifier` and `standardizer`).
- `PUT /api/v1/admin/models/{model_key}` — Switch between `default` and `custom` (with URL & optional API key).
- `POST /api/v1/admin/models/{model_key}/test` — Run a live diagnostic test on the active model.
- `GET /api/v1/admin/users` — List all admin users (`superadmin` only).
- `POST /api/v1/admin/users/invite` — Invite a new admin via Gmail (`superadmin` only).
- `PATCH /api/v1/admin/users/{id}` — Activate/deactivate or update role/password (`superadmin` only).
- `DELETE /api/v1/admin/users/{id}` — Remove an admin user (`superadmin` only).
- `GET /api/v1/admin/observability` — System metrics, recent audit logs, application log tail, and rate-limiter stats.
- `POST /api/v1/admin/protected-words` & `DELETE /api/v1/admin/protected-words/{id}` — Manage global protected English corpus words.

