from functools import lru_cache
import requests
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.translator")

_SESSION = requests.Session()
_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


@lru_cache(maxsize=2048)
def translate_english_to_tamil(english_text: str) -> str:
    """
    Translates English text to Tamil Unicode using Google's gtx translation endpoint
    with connection pooling, timeouts, and in-memory LRU caching.

    Args:
        english_text (str): The English text to translate.

    Returns:
        str: The translated Tamil text (or original text if unreachable).
    """
    if not english_text or not english_text.strip():
        return english_text

    try:
        response = _SESSION.get(
            _TRANSLATE_URL,
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "ta",
                "dt": "t",
                "q": english_text,
            },
            timeout=6,
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and data and isinstance(data[0], list):
                translated_segments = [
                    seg[0] for seg in data[0] if isinstance(seg, list) and seg and seg[0]
                ]
                if translated_segments:
                    return "".join(translated_segments)
        logger.warning(
            f"Translation returned unexpected response for '{english_text}': status={response.status_code}"
        )
    except Exception as e:
        logger.error(f"Error translating '{english_text}' to Tamil: {e}")

    return english_text
