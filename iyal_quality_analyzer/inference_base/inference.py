import os
import re
import threading
import time
import torch
import requests
from transformers import AutoTokenizer, BertForSequenceClassification
from iyal_quality_analyzer.utils.logger import setup_logging

# Disable Xet chunked CAS staging & symlink warnings for fast, reliable Docker volume caching
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

logger = setup_logging("iyal.classifier_model")


def _extract_hf_repo_from_url(url_or_repo: str) -> str:
    """
    If given a standard HuggingFace model page URL like
    'https://huggingface.co/sanujen/Tamil_Legacy_Roman_Classifier_V2',
    extracts 'sanujen/Tamil_Legacy_Roman_Classifier_V2'.
    Returns None if it is a custom REST API / inference endpoint URL.
    """
    if not url_or_repo:
        return None
    val = url_or_repo.strip()
    if not val.startswith(("http://", "https://")):
        return val
    match = re.match(r"^https?://huggingface\.co/([^/]+/[^/?#]+)/?$", val)
    if match:
        return match.group(1)
    return None


class Inference:
    """
    Performs sequence classification to distinguish between:
      - 0: 'Legacy Font Encoding' (e.g., Bamini 'tzf;fk;')
      - 1: 'Romanized Text Encoding' (e.g., Tanglish 'vanakkam')

    Supports both:
      - 'default' mode: Local BERT model inside Python venv / HuggingFace cache
      - 'custom' mode: Custom hosted HTTP inference endpoint URL or custom HuggingFace repo URL
    """

    DEFAULT_PRIMARY_REPO = "sanujen/Tamil_Legacy_Roman_Classifier_V2"
    DEFAULT_FALLBACK_REPO = "sanujen/fyp_0"

    def __init__(
        self,
        cache_dir=None,
        model_name="sanujen/Tamil_Legacy_Roman_Classifier_V2",
        model_version="version_1",
        mode: str = "default",
        custom_url: str = None,
        api_key: str = None,
        defer_load: bool = False,
    ):
        self.model_version = model_version
        self.cache_dir = cache_dir
        self.model_name = model_name or self.DEFAULT_PRIMARY_REPO
        self.mode = mode if mode in ("default", "custom") else "default"
        self.custom_url = custom_url.strip() if custom_url else None
        self.api_key = api_key.strip() if api_key else None

        self.label_mapping = {
            0: "Legacy Font Encoding",
            1: "Romanized Text Encoding",
            "LABEL_0": "Legacy Font Encoding",
            "LABEL_1": "Romanized Text Encoding",
            "Legacy Font Encoding": "Legacy Font Encoding",
            "Romanized Text Encoding": "Romanized Text Encoding",
        }

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self.active_source = "uninitialized"
        self.status = "initializing"
        self.last_error = None
        self.total_calls = 0
        self.last_latency_ms = 0.0
        self.avg_latency_ms = 0.0
        self._load_lock = threading.RLock()
        self._loaded = False

        if not defer_load:
            self.ensure_loaded()

    def ensure_loaded(self):
        """Thread-safe model initialization (can be called from background warmup or on first request)."""
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            self._load_or_configure()
            self._loaded = True

    def _load_local_hf_model(self, repo_candidates: list):
        """Attempts to load tokenizer & model from local cache first, then HF Hub."""
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)

        hf_token = os.getenv("HF_TOKEN") or None

        # 1. Try local HuggingFace cache first (instant, zero network calls)
        for repo in repo_candidates:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    repo, cache_dir=self.cache_dir, local_files_only=True
                )
                self.model = BertForSequenceClassification.from_pretrained(
                    repo, cache_dir=self.cache_dir, local_files_only=True
                )
                self.model.eval()
                self.model = self.model.to(self.device)
                self.active_source = f"local_cache:{repo}"
                self.status = "ready"
                logger.info(f"Loaded classifier model from local cache: {repo} on {self.device}")
                return True
            except Exception:
                continue

        # 2. Download from HuggingFace Hub if not in local cache
        for repo in repo_candidates:
            try:
                logger.info(f"Downloading classifier model from HuggingFace Hub: {repo}...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    repo, cache_dir=self.cache_dir, token=hf_token
                )
                self.model = BertForSequenceClassification.from_pretrained(
                    repo, cache_dir=self.cache_dir, token=hf_token
                )
                self.model.eval()
                self.model = self.model.to(self.device)
                self.active_source = f"hf_hub:{repo}"
                self.status = "ready"
                logger.info(f"Loaded classifier model from HuggingFace Hub: {repo} on {self.device}")
                return True
            except Exception as e:
                self.last_error = str(e)
                logger.warning(f"Could not load classifier repo '{repo}': {e}")

        return False

    def _load_or_configure(self):
        """Configures the classifier based on current mode ('default' or 'custom')."""
        self.last_error = None
        if self.mode == "custom" and self.custom_url:
            hf_repo = _extract_hf_repo_from_url(self.custom_url)
            if hf_repo:
                if self._load_local_hf_model([hf_repo]):
                    return
                raise RuntimeError(
                    f"Failed to load custom HuggingFace classifier model '{hf_repo}': {self.last_error}"
                )
            else:
                self.active_source = f"remote_url:{self.custom_url}"
                self.status = "ready_remote"
                logger.info(f"Configured classifier to use custom remote URL: {self.custom_url}")
                return

        # Default mode: try local cache of fyp_0 or V2 first so startup is instant, then online V2
        candidates = []
        if self.model_name:
            candidates.append(self.model_name)
        if self.DEFAULT_FALLBACK_REPO not in candidates:
            candidates.append(self.DEFAULT_FALLBACK_REPO)
        if self.DEFAULT_PRIMARY_REPO not in candidates:
            candidates.append(self.DEFAULT_PRIMARY_REPO)

        if not self._load_local_hf_model(candidates):
            self.active_source = "heuristic_fallback"
            self.status = "degraded_fallback"
            logger.warning(
                "Classifier ML weights unavailable offline; using rule-based heuristic fallback."
            )

    def _heuristic_classify(self, word: str) -> str:
        """Fallback classifier if model weights or remote endpoint fail."""
        legacy_indicators = set(";`\\[]{}^~@#$%&*+=<>|")
        if any(ch in legacy_indicators for ch in word):
            return "Legacy Font Encoding"
        cleaned = word.strip(".,!?'\"()")
        if cleaned and not (cleaned.islower() or cleaned.isupper() or cleaned.istitle()):
            return "Legacy Font Encoding"
        return "Romanized Text Encoding"

    def _remote_inference(self, word: str) -> str:
        """Calls a custom hosted HTTP inference endpoint."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"inputs": word, "input_text": word, "word": word}
        resp = requests.post(self.custom_url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, list) and first:
                first = max(first, key=lambda x: x.get("score", 0))
            if isinstance(first, dict) and "label" in first:
                lbl = first["label"]
                return self.label_mapping.get(lbl, str(lbl))

        if isinstance(data, dict):
            for key in ("label", "prediction", "inputType", "output", "encoding_type"):
                if key in data:
                    val = data[key]
                    return self.label_mapping.get(val, str(val))

        raise ValueError(f"Unrecognized response structure from custom classifier URL: {data}")

    def inference(self, word: str) -> str:
        """
        Performs inference on the given word and returns 'Legacy Font Encoding' or 'Romanized Text Encoding'.
        """
        self.ensure_loaded()
        t0 = time.perf_counter()
        try:
            if self.mode == "custom" and self.custom_url and self.status == "ready_remote":
                predicted_label = self._remote_inference(word)
            elif self.model is not None and self.tokenizer is not None:
                inputs = self.tokenizer(
                    word, return_tensors="pt", truncation=True, padding=True, max_length=180
                )
                inputs = {key: val.to(self.device) for key, val in inputs.items()}
                with torch.no_grad():
                    logits = self.model(**inputs).logits
                    pred_idx = int(torch.argmax(logits, dim=1).item())
                predicted_label = self.label_mapping.get(pred_idx, "Romanized Text Encoding")
            else:
                predicted_label = self._heuristic_classify(word)
            return predicted_label
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Classifier inference error on '{word}': {e}. Using heuristic fallback.")
            return self._heuristic_classify(word)
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.total_calls += 1
            self.last_latency_ms = round(elapsed_ms, 2)
            self.avg_latency_ms = round(
                ((self.avg_latency_ms * (self.total_calls - 1)) + elapsed_ms) / self.total_calls,
                2,
            )

    def get_info(self) -> dict:
        return {
            "model_key": "classifier",
            "name": "Legacy vs. Romanized Classifier",
            "mode": self.mode,
            "default_model_name": self.model_name,
            "custom_url": self.custom_url,
            "has_api_key": bool(self.api_key),
            "active_source": self.active_source,
            "status": self.status,
            "device": str(self.device),
            "total_calls": self.total_calls,
            "last_latency_ms": self.last_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "last_error": self.last_error,
        }
