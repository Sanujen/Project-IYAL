# Project IYAL v2.0 — Comprehensive Implementation & Architecture Report

## 1. Executive Summary
Project IYAL (**இயல்: Input Text Normalizer for Tamil Language**) has been completely re-engineered from a multi-container Streamlit + FastAPI + PostgreSQL prototype into a high-performance, zero-cost, security-hardened **Monolithic FastAPI Web Application & NLP Engine**.

Key achievements:
- **Repository Cleanup**: Removed all non-runtime research artifacts (`error_analyzis/`, `training/`, `imgs/`, `docs/build/`, legacy `feedback/`, and old `ui/`).
- **Monolithic Architecture**: Consolidated the Public UI (`/`), Admin Portal (`/admin`), REST APIs (`/api/v1/*` + legacy endpoints), DDoS/Brute-Force security middleware, and embedded SQLite WAL database into a single server.
- **1000x Pipeline Optimizations & Bug Fixes**: Fixed per-word NLTK corpus rebuilding, per-word legacy font set recomputation, `/get_encoding/` memory leaks, `googletrans`/`httpx==0.13.3` dependency conflicts, and Bamini pulli (`;`) stripping bugs.
- **Admin Portal (`/admin`) with Hybrid Gmail RBAC & Dual-Model Hot-Swap**: Predefined `superadmin` can invite `admin` users via Gmail, manage feedback, view live observability/security logs, and switch either ML model (`classifier` or `standardizer`) between `default` (local venv) and `custom` (hosted URL / HuggingFace repo).

---

## 2. System Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Browser Clients"]
        PublicUI["Public Normalizer SPA (/)"]
        AdminUI["Protected Admin Portal (/admin)"]
    end

    subgraph Monolith["Single Monolithic FastAPI Server (server/server.py)"]
        SecMW["MonolithSecurityMiddleware<br/>(IP Rate Limiter, Auto-Ban, Payload Guard, X-Request-ID)"]
        Auth["Hybrid Auth & RBAC Engine<br/>(Superadmin + Gmail Invite + Google OAuth2 + JWT)"]
        Router["REST API Router<br/>(/api/v1/* & Legacy Routes)"]
        ModelMgr["Dynamic Dual-Model Manager<br/>(Default Local Venv vs. Custom Hosted URL)"]
        Obs["Observability Engine<br/>(Rotating Logs + Ring Buffer + Audit Trail)"]
    end

    subgraph Pipeline["11-Step Normalization Engine (iyal_quality_analyzer)"]
        Seg["Step 1-2: Sentence & Token Segmenter"]
        UniClass["Step 3-4: Unicode Range Classifier"]
        Corpus["Step 5: Cached NLTK Corpus + UI Protected Words"]
        ClfModel["Step 6: Model 1 — Legacy vs. Romanized Classifier"]
        LegacyConv["Step 7: encode2unicode (25 Legacy Fonts + UI Confirm)"]
        Translit["Step 8: Cached Tamil Transliterator"]
        Translate["Step 10: Optional English-to-Tamil Translator"]
        StdModel["Step 11: Model 2 — mBART Colloquial-to-Standard"]
    end

    subgraph Storage["Zero-Cost Persistent Storage (Docker Volumes)"]
        SQLite[("SQLite WAL DB<br/>(./data/iyal.db)")]
        LogFiles[("Rotating Log Files<br/>(./logs/app.log, error.log)")]
        HFCache[("HuggingFace Model Cache<br/>(./model_cache)")]
    end

    PublicUI --> SecMW
    AdminUI --> SecMW
    SecMW --> Auth
    SecMW --> Router
    Router --> Pipeline
    Router --> ModelMgr
    Router --> SQLite
    Obs --> LogFiles
    Obs --> SQLite
    ModelMgr --> ClfModel
    ModelMgr --> StdModel
    ClfModel --> HFCache
    StdModel --> HFCache
    Seg --> UniClass --> Corpus --> ClfModel
    ClfModel --> LegacyConv
    ClfModel --> Translit
    LegacyConv --> Translate --> StdModel
    Translit --> Translate
```

---

## 3. The 11-Step Normalization Workflow Diagram

```mermaid
flowchart TD
    Start(["Step 1: User Inputs Paragraph or Uploads .docx/.txt/.pdf"]) --> Step2["Step 2: Sentence Segmentation & Word Tokenization"]
    Step2 --> SpecialCheck{"Is Special Case?<br/>(URL, Email, Phone, [Tag])"}
    SpecialCheck -- Yes --> KeepSpecial["Tag: special_case (Keep As-Is)"]
    SpecialCheck -- No --> ProtectedCheck{"Step 5a: In User/Admin<br/>Protected Corpus?"}
    ProtectedCheck -- Yes --> KeepProtected["Tag: protected_en<br/>(Never Transliterate or Translate)"]
    ProtectedCheck -- No --> Step4{"Step 3 & 4: Unicode Script Category"}

    Step4 -- "raw_tamil / numeric" --> KeepRaw["Keep Raw Tamil / Numeric As-Is"]
    Step4 -- "en_tamil / en_numeric" --> TranslitMixed["Transliterate English Part to Tamil Unicode"]
    Step4 -- "Non-Tamil ASCII ('english')" --> Step5b{"Step 5b: In Cached<br/>NLTK English Corpus?"}

    Step5b -- Yes --> TagEn["Tag: en (English Word)"]
    Step5b -- No --> Step6["Step 6: Model 1 (BERT Classifier)<br/>Legacy vs. Romanized"]

    Step6 -- "Legacy Font Encoding" --> Step7["Step 7: Auto-Detect Legacy Font (25 Encodings)<br/>Show Live Preview & Confirm in UI -> encode2unicode"]
    Step6 -- "Romanized Text Encoding" --> Step8["Step 8: Transliterate Tanglish to Tamil Unicode"]

    KeepSpecial --> Step9["Step 9: Reconstruct Sentence & Paragraph"]
    KeepProtected --> Step9
    KeepRaw --> Step9
    TranslitMixed --> Step9
    Step7 --> Step9
    Step8 --> Step9
    TagEn --> Step10{"Step 10: Optional Checkbox<br/>need_translation?"}
    Step10 -- Yes --> DoTranslate["Translate Contiguous English Words to Tamil<br/>(Protected Words Skipped)"]
    Step10 -- No --> Step9
    DoTranslate --> Step9

    Step9 --> Step11{"Step 11: Optional Checkbox<br/>colloquial_to_standard?"}
    Step11 -- Yes --> DoStandardize["Run Model 2 (mBART Standardizer)<br/>Convert Colloquial Tamil to Formal Tamil"]
    Step11 -- No --> Final(["Return Normalized Paragraph & Token Breakdown to UI"])
    DoStandardize --> Final
```

---

## 4. Admin Authentication, Gmail Invitation & RBAC Flow

```mermaid
sequenceDiagram
    participant SA as Superadmin (Predefined)
    participant API as FastAPI Monolith (/api/v1/auth & /admin)
    participant DB as SQLite WAL Database
    participant Inv as Invited Gmail Admin
    participant Google as Google OAuth2 (tokeninfo)

    SA->>API: POST /api/v1/auth/login (SUPERADMIN_USERNAME + PASSWORD)
    API->>DB: Verify PBKDF2-SHA256 hash & check brute-force state
    API-->>SA: Return signed JWT + Set HttpOnly Cookie (role=superadmin)

    SA->>API: POST /api/v1/admin/users/invite (email="colleague@gmail.com", role="admin")
    API->>DB: Create AdminUser row with invite_token & temporary_password
    API-->>SA: Return Invite Token & Temporary Credentials

    alt Sign in via Google OAuth 2.0 (when GOOGLE_CLIENT_ID configured)
        Inv->>Google: Click "Sign in with Google"
        Google-->>Inv: Google ID Token
        Inv->>API: POST /api/v1/auth/google (id_token)
        API->>Google: Verify ID Token signature & email_verified
        API->>DB: Verify colleague@gmail.com exists in admin_users & is_active
        API-->>Inv: Return JWT (role=admin)
    else Sign in via Invite Token / Password (works on raw University IPs)
        Inv->>API: POST /api/v1/auth/accept-invite (email, invite_token, new_password)
        API->>DB: Verify invite_token, update password_hash, clear invite_token
        API-->>Inv: Return JWT (role=admin)
    end
```

---

## 5. Findings, Bugs Discovered & Recommendations During Testing

### Bugs Found in Original Codebase & Fixed in v2.0
1. **Severe Memory Leak & Latency in `/get_encoding/` (`server/server.py` line 174)**:
   - *Issue*: The original `/get_encoding/` endpoint instantiated a brand-new `Inference()` BERT model on **every HTTP request** (`inference_model = Inference()`), reloading ~438 MB of weights each time instead of reusing the startup singleton.
   - *Fix*: Reused the managed `model_manager.classifier` singleton across all requests.
2. **Per-Word NLTK Corpus Re-initialization (`english_word_check.py`)**:
   - *Issue*: `set(words.words())` (236,736 words) was reconstructed from disk on every single word token, and included single letters (`'f'`, `'m'`, `'c'`, `'v'`) and 2-letter strings (`'th'`, `'fh'`, `'gh'`) that collide with common Bamini Tamil syllables (`க`, `அ`, `உ`, `எ`, `வா`, `கா`, `பா`).
   - *Fix*: Cached `_ENGLISH_VOCAB` once in memory as a `frozenset`, removed Bamini syllable collisions, excluded tokens containing legacy punctuation markers (`;`), and added user-configurable Protected Corpus words.
3. **Bamini Pulli (`;`) Stripping Bug in `auto_detect_encoding` (`legacy_converter.py`)**:
   - *Issue*: `_get_unique_ch()` stripped `;` as a "special character" before matching unique encoding keys. In Bamini, `;` is the Tamil pulli (`்`). Stripping `;` turned `"cyfk;"` (`உலகம்`) into `"cyf"`, which falsely matched `"yf"` in `mylai2utf8` instead of `bamini2utf8`, and returned `None` when no match was found (breaking `ui/main.py`'s `if not auto_encoding == "legacy_font_not_found"` check).
   - *Fix*: Added Bamini `<consonant>;` pulli signature detection prior to stripping `;`, precomputed unique/common character sets at module import time (1000x speedup), and standardized `"legacy_font_not_found"` return values.
4. **Dependency Conflict in `requirements.txt` (`googletrans==3.1.0a0` & `httpx==0.13.3`)**:
   - *Issue*: `googletrans==3.1.0a0` pinned `httpx==0.13.3` and `httpcore==0.9.0`, conflicting with modern `fastapi`, `uvicorn`, and `huggingface-hub`.
   - *Fix*: Replaced with direct, connection-pooled, `@lru_cache`-backed `requests.Session()` calls to Google's Input Tools and `gtx` translation endpoints.
5. **HuggingFace Model Cache & `mBART` Loading (`inference.py` & `inference_coll_to_stand.py`)**:
   - *Finding*: On HuggingFace Hub, `sanujen/mBART_Tamil_Colloquial_to_Standard` has `optimizer.pt` (4.88 GB) committed in the repo alongside `model.safetensors` (2.44 GB), and its HF Hub `pipeline_tag` is `text-generation` rather than `text2text-generation`.
   - *Fix & Recommendation*: Switched `inference_coll_to_stand.py` to use `AutoTokenizer` + `AutoModelForSeq2SeqLM.from_pretrained` (which downloads only `model.safetensors` and ignores the 4.88 GB `optimizer.pt`) and checks the local HuggingFace cache (`local_files_only=True`) first before attempting network downloads. **Recommendation for repo owners**: Delete `optimizer.pt`, `scheduler.pt`, and `rng_state.pth` from the HuggingFace repo `sanujen/mBART_Tamil_Colloquial_to_Standard` to keep the HuggingFace repository clean.

