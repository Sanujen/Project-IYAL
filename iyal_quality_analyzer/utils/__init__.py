from .unicode_classifier import classify_unicode
from .transliteration import transliterate
from .legacy_converter.legacy_converter import (
    convert_legacy_to_unicode,
    auto_detect_encoding,
    ALL_ENCODINGS,
)
from .translator import translate_english_to_tamil
from .english_word_check import (
    is_english_word,
    is_protected_word,
    set_global_protected_words,
    get_global_protected_words,
)
from .special_case_check import is_special_case

__all__ = [
    "classify_unicode",
    "transliterate",
    "convert_legacy_to_unicode",
    "auto_detect_encoding",
    "ALL_ENCODINGS",
    "translate_english_to_tamil",
    "is_english_word",
    "is_protected_word",
    "set_global_protected_words",
    "get_global_protected_words",
    "is_special_case",
]
