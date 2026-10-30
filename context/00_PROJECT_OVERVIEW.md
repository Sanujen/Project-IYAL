# Project IYAL — AI Agent Context & Overview

## 1. Purpose of This Directory
This `context/` directory is the persistent memory and architectural source of truth for AI coding agents working on **Project IYAL** (இயல்: Input Text Normalizer for Tamil Language). Any new AI session should read the files in `context/` first before making changes:

1. `00_PROJECT_OVERVIEW.md` — Domain pipeline (11 steps), core problem statement, and repository layout.
2. `01_ARCHITECTURE_DECISIONS.md` — Key technical decisions (Monolithic FastAPI server, SQLite/SQLAlchemy zero-cost DB, Hybrid Gmail/OAuth2 + Password RBAC, In-Monolith DDoS/Brute-Force defense, Dynamic Dual-Model Manager).
3. `02_API_AND_DATA_SCHEMA.md` — Database tables, REST API endpoints, and payload schemas.
4. `03_SESSION_STATE.md` — Phase-by-phase implementation tracker, test findings, and current state.
5. `04_RECOMMENDED_ADDONS.md` — Phase 5 future high-value add-ons roadmap (documented for future phases, intentionally not implemented in initial phases).

---

## 2. Domain Flow (The 11-Step Normalization Pipeline)

1. **Paragraph Input**: Users input a paragraph (or upload `.txt`, `.docx`, `.pdf`) containing Tamil, Tanglish (Romanized Tamil), Legacy Tamil font encodings (e.g., Bamini, Anjal, TSCII), and/or English words.
2. **Sentence & Token Segmentation**: The paragraph is segmented into sentences (preserving URLs, emails, phone numbers, brackets, and punctuation) and tokenized word-by-word.
3. **Word Type Taxonomy (5 Types)**:
   - **3 Main Unicode Categories**:
     1. `raw_tamil` — Pure Tamil Unicode (`U+0B80`–`U+0BFF`). Left as-is.
     2. `en_tamil` — Mixed Tamil + English Unicode in a single token (e.g., `வணkkam`). Transliterated into Tamil Unicode (`வணக்கம்`).
     3. **Non-Tamil Unicode (ASCII/Latin)** — Further divided into:
        - `en` / `protected_en` — English word (found in the NLTK English corpus or in the user-supplied Custom Protected Words list).
        - `Legacy Font Encoding` — Legacy Tamil font token (e.g., Bamini `tzf;fk;`).
        - `Romanized Text Encoding` — Romanized Tamil / Tanglish token (e.g., `vanakkam`).
   - Plus auxiliary handling for `numeric`, `en_numeric`, and `special_case` (URLs, emails, phone numbers, `[bracketed]` tags).
4. **Unicode Range Classification**: Fast character codepoint inspection classifies each token into Raw Tamil, Tamil+English, Non-Tamil (ASCII/Latin), Numeric, or Mixed Alphanumeric.
5. **English & Custom Protected Corpus Check**: Non-Tamil Unicode words are checked against:
   - **User/Admin Custom Protected Words** (words entered via the UI that must **never** be transliterated or translated).
   - **NLTK English Vocabulary Corpus** (cached in memory as a `frozenset` for $O(1)$ lookup).
6. **Legacy vs. Romanized Classification (Model 1)**: If a Non-Tamil token is **not** an English word, it is classified by our fine-tuned BERT sequence classifier (`sanujen/Tamil_Legacy_Roman_Classifier_V2` / `sanujen/fyp_0`) into either:
   - `Legacy Font Encoding`
   - `Romanized Text Encoding`
7. **Legacy Font Identification & User Confirmation (`encode2unicode`)**:
   - If a token is classified as `Legacy Font Encoding`, the `auto_detect_encoding` algorithm identifies the specific legacy font (out of 25 supported encodings such as `bamini2utf8`, `anjal2utf8`, `tscii2utf8`, etc.) using precomputed unique compound character signatures.
   - **UI Confirmation Step**: The detected legacy font style (along with a sample preview) is shown to the user in the UI for confirmation (with ability to override from the 25 font styles) before executing the full conversion with `encode2unicode`.
8. **Transliteration for Non-Legacy (Romanized) Words**: Tokens classified as `Romanized Text Encoding` are transliterated to Tamil Unicode via the Google Input Tools Tamil transliteration service (with in-memory LRU caching).
9. **Sentence & Paragraph Restructuring**: All normalized tokens are reassembled into sentences with their original punctuation and then reconstructed into the full paragraph.
10. **Optional English-to-Tamil Translation**: If the user checks **"Translate English Words"** (`need_translation=True`), contiguous English (`en`) tokens are grouped into phrases and translated into Tamil (while keeping user-specified `protected_en` words untouched).
11. **Optional Colloquial-to-Standard Tamil Standardization (Model 2)**: If the user checks **"Colloquial to Standard Tamil"** (`colloquial_to_standard=True`), each reconstructed Tamil sentence is passed through our fine-tuned mBART sequence-to-sequence standardizer (`sanujen/mBART_Tamil_Colloquial_to_Standard`) to produce formal written Tamil.

