from .unicode_classifier import classify_unicode
from .transliteration import transliterate
from .legacy_converter.legacy_converter import convert_legacy_to_unicode, auto_detect_encoding
from .translator import translate_english_to_tamil
from .english_word_check import is_english_word
from .special_case_check import is_special_case

__all__ = [
    "classify_unicode",
    "transliterate",
    "convert_legacy_to_unicode",
    "translate_english_to_tamil",
    "is_english_word",
    "is_special_case",
]