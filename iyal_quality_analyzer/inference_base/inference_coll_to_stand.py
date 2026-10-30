import os
import re
import time
import torch
import requests
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.standardizer_model")


def _extract_hf_repo_from_url(url_or_repo: str) -> str:
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
    Performs Colloquial Tamil to Standard Written Tamil conversion using a fine-tuned
    mBART sequence-to-sequence model ('sanujen/mBART_Tamil_Colloquial_to_Standard').

    Supports both:
      - 'default' mode: Local mBART model inside Python venv / HuggingFace cache
      - 'custom' mode: Custom hosted HTTP inference endpoint URL or custom HuggingFace repo URL
    """

    DEFAULT_REPO = "sanujen/mBART_Tamil_Colloquial_to_Standard"

    def __init__(
        self,
        cache_dir=None,
        model_name="sanujen/mBART_Tamil_Colloquial_to_Standard",
        model_version="version_1",
        mode: str = "default",
        custom_url: str = None,
        api_key: str = None,
    ):
        self.model_version = model_version
        self.cache_dir = cache_dir  # None uses default ~/.cache/huggingface/hub
        self.model_name = model_name or self.DEFAULT_REPO
        self.mode = mode if mode in ("default", "custom") else "default"
        self.custom_url = custom_url.strip() if custom_url else None
        self.api_key = api_key.strip() if api_key else None

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self.active_source = "uninitialized"
        self.status = "initializing"
        self.last_error = None
        self.total_calls = 0
        self.last_latency_ms = 0.0
        self.avg_latency_ms = 0.0

        self._load_or_configure()

    def _load_local_hf_model(self, repo: str) -> bool:
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)

        # 1. Try local HuggingFace cache first
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                repo, cache_dir=self.cache_dir, local_files_only=True
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                repo, cache_dir=self.cache_dir, local_files_only=True
            )
            self.model.eval()
            self.model = self.model.to(self.device)
            self.active_source = f"local_cache:{repo}"
            self.status = "ready"
            logger.info(f"Loaded mBART standardizer from local cache: {repo} on {self.device}")
            return True
        except Exception:
            pass

        # 2. Download from HuggingFace Hub
        try:
            logger.info(f"Downloading mBART standardizer from HuggingFace Hub: {repo}...")
            self.tokenizer = AutoTokenizer.from_pretrained(repo, cache_dir=self.cache_dir)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(repo, cache_dir=self.cache_dir)
            self.model.eval()
            self.model = self.model.to(self.device)
            self.active_source = f"hf_hub:{repo}"
            self.status = "ready"
            logger.info(f"Loaded mBART standardizer from HuggingFace Hub: {repo} on {self.device}")
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"Could not load mBART standardizer '{repo}': {e}")
            return False

    def _load_or_configure(self):
        self.last_error = None
        if self.mode == "custom" and self.custom_url:
            hf_repo = _extract_hf_repo_from_url(self.custom_url)
            if hf_repo:
                if self._load_local_hf_model(hf_repo):
                    return
                raise RuntimeError(
                    f"Failed to load custom HuggingFace standardizer model '{hf_repo}': {self.last_error}"
                )
            else:
                self.active_source = f"remote_url:{self.custom_url}"
                self.status = "ready_remote"
                logger.info(f"Configured standardizer to use custom remote URL: {self.custom_url}")
                return

        if not self._load_local_hf_model(self.model_name):
            self.active_source = "passthrough_fallback"
            self.status = "degraded_fallback"
            logger.warning(
                "Standardizer ML weights unavailable; using passthrough fallback."
            )

    def _remote_inference(self, sentence: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"inputs": sentence, "input_text": sentence, "sentence": sentence}
        resp = requests.post(self.custom_url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        # Parse HuggingFace Inference API format: [{"generated_text": "..."}] or [{"translation_text": "..."}]
        if isinstance(data, list) and data and isinstance(data[0], dict):
            for k in ("generated_text", "translation_text", "standard_tamil", "output"):
                if k in data[0]:
                    return str(data[0][k])

        if isinstance(data, dict):
            for k in ("standard_tamil", "generated_text", "translation_text", "output"):
                if k in data:
                    return str(data[k])

        raise ValueError(f"Unrecognized response structure from custom standardizer URL: {data}")

    def inference(self, sentence: str) -> str:
        """
        Converts a colloquial Tamil sentence into standard formal Tamil.
        """
        if not sentence or not sentence.strip():
            return sentence

        t0 = time.perf_counter()
        try:
            if self.mode == "custom" and self.custom_url and self.status == "ready_remote":
                return self._remote_inference(sentence)
            elif self.model is not None and self.tokenizer is not None:
                inputs = self.tokenizer(
                    sentence,
                    return_tensors="pt",
                    truncation=True,
                    max_length=256,
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                with torch.no_grad():
                    generated_ids = self.model.generate(**inputs, max_new_tokens=256)
                decoded = self.tokenizer.batch_decode(
                    generated_ids, skip_special_tokens=True
                )
                return decoded[0].strip() if decoded else sentence
            else:
                return sentence
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Standardizer inference error on '{sentence}': {e}")
            return sentence
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
            "model_key": "standardizer",
            "name": "Colloquial-to-Standard Tamil Standardizer (mBART)",
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
