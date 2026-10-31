from typing import Dict, Optional
import requests
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.translator")

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }
)

_GTX_URL = "https://translate.googleapis.com/translate_a/single"
_CLIENTS5_URL = "https://clients5.google.com/translate_a/t"
_MYMEMORY_URL = "https://api.mymemory.translated.net/get"

# Only successful translations are cached here so transient 429/network errors never poison the cache
_TRANSLATION_CACHE: Dict[str, str] = {}
_MAX_CACHE_SIZE = 4096


def _contains_tamil_unicode(text: str) -> bool:
    return any(0x0B80 <= ord(ch) <= 0x0BFF for ch in text)


def _try_google_single(english_text: str, client_name: str = "gtx") -> Optional[str]:
    resp = _SESSION.get(
        _GTX_URL,
        params={
            "client": client_name,
            "sl": "en",
            "tl": "ta",
            "dt": "t",
            "q": english_text,
        },
        timeout=6,
    )
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and data and isinstance(data[0], list):
            segments = [
                seg[0] for seg in data[0] if isinstance(seg, list) and seg and seg[0]
            ]
            if segments:
                return "".join(segments).strip()
    return None


def _try_google_clients5(english_text: str) -> Optional[str]:
    resp = _SESSION.get(
        _CLIENTS5_URL,
        params={
            "client": "dict-chrome-ex",
            "sl": "en",
            "tl": "ta",
            "q": english_text,
        },
        timeout=6,
    )
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, str) and first.strip():
                return first.strip()
            if isinstance(first, list) and first and isinstance(first[0], str):
                return first[0].strip()
        elif isinstance(data, dict) and "sentences" in data:
            parts = [
                s.get("trans", "")
                for s in data["sentences"]
                if isinstance(s, dict) and s.get("trans")
            ]
            if parts:
                return "".join(parts).strip()
    return None


def _try_mymemory(english_text: str) -> Optional[str]:
    resp = _SESSION.get(
        _MYMEMORY_URL,
        params={"q": english_text, "langpair": "en|ta"},
        timeout=6,
    )
    if resp.status_code == 200:
        data = resp.json()
        translated = (
            data.get("responseData", {}).get("translatedText", "")
            if isinstance(data, dict)
            else ""
        )
        if translated and _contains_tamil_unicode(translated):
            return translated.strip()
    return None


def translate_english_to_tamil(english_text: str) -> str:
    """
    Translates English text to Tamil Unicode using a multi-endpoint fallback chain
    (Google gtx -> Google clients5 -> Google dict-chrome-ex -> MyMemory)
    with browser User-Agent headers and failure-safe in-memory caching.

    Args:
        english_text (str): The English text to translate.

    Returns:
        str: The translated Tamil text (or original text if all providers are unreachable).
    """
    if not english_text or not english_text.strip():
        return english_text

    key = english_text.strip()
    if key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[key]

    providers = (
        ("google_gtx", lambda: _try_google_single(key, "gtx")),
        ("google_clients5", lambda: _try_google_clients5(key)),
        ("google_chrome_ex", lambda: _try_google_single(key, "dict-chrome-ex")),
        ("mymemory", lambda: _try_mymemory(key)),
    )

    for name, fn in providers:
        try:
            translated = fn()
            if translated:
                if len(_TRANSLATION_CACHE) >= _MAX_CACHE_SIZE:
                    _TRANSLATION_CACHE.clear()
                _TRANSLATION_CACHE[key] = translated
                return translated
        except Exception as e:
            logger.debug(f"Translation provider '{name}' failed for '{key}': {e}")

    logger.warning(f"All translation providers failed for '{key}'; returning original text.")
    return english_text
