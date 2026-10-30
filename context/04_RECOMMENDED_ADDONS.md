# Recommended High-Value Add-Ons (Phase 5 Roadmap)

> **Note**: Per project instructions, these high-value add-ons are documented here as the **final phase roadmap** and are intentionally **not** implemented in the initial phases so the core platform remains lightweight, fast, and focused.

---

## 1. Active Learning & One-Click Feedback-to-Dataset Pipeline
- **Problem**: Users submit feedback when a word is misclassified (e.g., a rare Bamini token classified as Romanized Tanglish, or a colloquial phrase imperfectly standardized), but admins currently only read the feedback manually.
- **Add-On Design**:
  - Add an **"Approve as Training Sample"** button on each feedback card in `/admin`.
  - Allow admins to correct the expected target token/sentence and export approved rows directly as HuggingFace-compatible CSV/JSONL datasets for periodic LoRA / full fine-tuning of Model 1 (`Classifier`) and Model 2 (`mBART Standardizer`).

## 2. Browser Extension & OS-Wide Input IME Companion
- **Problem**: Users frequently read legacy-encoded Tamil PDFs/websites or type Tanglish in external editors (Google Docs, Word, WhatsApp Web, Email).
- **Add-On Design**:
  - A lightweight **Chrome/Firefox WebExtension** that connects to the university-hosted Project IYAL `/api/v1/analyze` endpoint.
  - Highlights legacy Bamini/TSCII text on any webpage and converts it in-place via right-click context menu.

## 3. Offline Rule-Based & ONNX Quantized Fast-Path Transliteration
- **Problem**: Currently, Romanized Tamil (`vanakkam -> வணக்கம்`) and English-to-Tamil translation rely on external Google web endpoints (`inputtools.google.com` and `translate.googleapis.com`). If the university server loses external internet access or gets rate-limited by Google, transliteration falls back unless cached.
- **Add-On Design**:
  - Integrate an offline phonetic Tamil transliteration table / IndicXlit ONNX int8 model inside the venv as an automatic offline fallback when Google Input Tools is unreachable.
  - Quantize `sanujen/Tamil_Legacy_Roman_Classifier_V2` and `sanujen/mBART_Tamil_Colloquial_to_Standard` to **ONNX Runtime INT8**, reducing RAM usage by ~65% and speeding up CPU inference by 3–4x.

## 4. OCR & Scanned Tamil Document Normalization
- **Problem**: Many uploaded `.pdf` files in Tamil archives are scanned images rather than selectable text PDFs.
- **Add-On Design**:
  - Integrate `Tesseract OCR` (`tam+eng` language packs) as an optional fallback in `file_parser.py` when `PyPDF2` extracts 0 characters from a scanned PDF page.

## 5. Batch Corpus & Dialect Analytics Dashboard
- **Problem**: Researchers using Project IYAL often want to normalize thousands of sentences in `.csv` or `.jsonl` format and analyze dialect distributions (e.g., Jaffna Tamil vs. Chennai Tamil vs. Kongu Tamil colloquialisms).
- **Add-On Design**:
  - Asynchronous background batch job processor in FastAPI (`BackgroundTasks` + downloadable ZIP results) with dialect classification tagging.

