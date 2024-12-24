from .unicode_classifier import classify_unicode
from .transliteration import transliterate
from .legacy_converter.legacy_converter import convert_legacy_to_unicode
from .translator import translate_english_to_tamil

__all__ = [
    "classify_unicode",
    "transliterate",
    "convert_legacy_to_unicode",
    "translate_english_to_tamil",
]