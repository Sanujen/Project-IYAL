from typing import Dict
import requests
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.transliteration")

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
_INPUTTOOLS_URL = "https://inputtools.google.com/request"

# Only cache successful transliterations so transient network errors are never cached
_TRANSLITERATION_CACHE: Dict[str, str] = {}
_MAX_CACHE_SIZE = 8192


def transliterate(input_text: str) -> str:
    """
    Transliterates Romanized Tamil (Tanglish) text into Tamil Unicode using
    Google Input Tools API with connection pooling and failure-safe caching.

    Args:
        input_text (str): The Romanized Tamil text to transliterate.

    Returns:
        str: The transliterated Tamil Unicode text (or original text on fallback).
    """
    if not input_text or not input_text.strip():
        return input_text

    if input_text in _TRANSLITERATION_CACHE:
        return _TRANSLITERATION_CACHE[input_text]

    try:
        response = _SESSION.get(
            _INPUTTOOLS_URL,
            params={
                "text": input_text,
                "itc": "ta-t-i0-und",
                "num": 1,
                "cp": 0,
                "cs": 1,
                "ie": "utf-8",
                "oe": "utf-8",
                "app": "iyal-normalizer",
            },
            timeout=6,
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) >= 2 and data[0] == "SUCCESS":
                candidates_list = data[1]
                out_parts = []
                for item in candidates_list:
                    if len(item) >= 2 and item[1]:
                        out_parts.append(item[1][0])
                    elif len(item) >= 1:
                        out_parts.append(item[0])
                if out_parts:
                    result = "".join(out_parts)
                    if len(_TRANSLITERATION_CACHE) >= _MAX_CACHE_SIZE:
                        _TRANSLITERATION_CACHE.clear()
                    _TRANSLITERATION_CACHE[input_text] = result
                    return result
        logger.warning(
            f"Transliteration returned non-success for '{input_text}': status={response.status_code}"
        )
    except Exception as e:
        logger.error(f"Transliteration error for '{input_text}': {e}")

    # Graceful fallback: try google-transliteration-api if installed, else return input_text
    try:
        from google.transliteration import transliterate_text

        result = transliterate_text(input_text, lang_code="ta")
        if result:
            _TRANSLITERATION_CACHE[input_text] = result
            return result
    except Exception:
        pass

    return input_text
