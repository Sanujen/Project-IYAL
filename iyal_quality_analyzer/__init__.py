from iyal_quality_analyzer.utils.legacy_converter.legacy_converter import (
    convert_legacy_to_unicode,
    auto_detect_encoding,
    ALL_ENCODINGS,
)
from iyal_quality_analyzer.utils.unicode_classifier import classify_unicode
from iyal_quality_analyzer.utils.transliteration import transliterate
from iyal_quality_analyzer.utils.translator import translate_english_to_tamil
from iyal_quality_analyzer.inference_base.inference import Inference
from iyal_quality_analyzer.inference_base.inference_coll_to_stand import (
    Inference as CollToStandInference,
)
from iyal_quality_analyzer.quality_analyzer import (
    quality_analyzer,
    multi_sentence_quality_analyzer,
    single_sentence_quality_analyzer,
    single_word_quality_analyzer,
    get_encoding_fun,
    detect_legacy_encoding_details,
    sentence_segmentation,
)
from iyal_quality_analyzer.utils.english_word_check import (
    is_english_word,
    is_protected_word,
    set_global_protected_words,
    get_global_protected_words,
)
from iyal_quality_analyzer.utils.special_case_check import is_special_case

__all__ = [
    "convert_legacy_to_unicode",
    "auto_detect_encoding",
    "ALL_ENCODINGS",
    "classify_unicode",
    "transliterate",
    "translate_english_to_tamil",
    "Inference",
    "CollToStandInference",
    "quality_analyzer",
    "multi_sentence_quality_analyzer",
    "single_sentence_quality_analyzer",
    "single_word_quality_analyzer",
    "get_encoding_fun",
    "detect_legacy_encoding_details",
    "sentence_segmentation",
    "is_english_word",
    "is_protected_word",
    "set_global_protected_words",
    "get_global_protected_words",
    "is_special_case",
]
