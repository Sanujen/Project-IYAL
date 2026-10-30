#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict
from iyal_quality_analyzer.utils.legacy_converter.encode2utf8 import (
    anjal2utf8,
    bamini2utf8,
    boomi2utf8,
    dinakaran2utf8,
    dinamani2utf8,
    dinathanthy2utf8,
    kavipriya2utf8,
    murasoli2utf8,
    mylai2utf8,
    nakkeeran2utf8,
    roman2utf8,
    tab2utf8,
    tam2utf8,
    tscii2utf8,
    pallavar2utf8,
    indoweb2utf8,
    koeln2utf8,
    libi2utf8,
    oldvikatan2utf8,
    webulagam2utf8,
    diacritic2utf8,
    shreelipi2utf8,
    softview2utf8,
    tace2utf8,
    vanavil2utf8,
)
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.legacy_converter")

ALL_ENCODINGS = [
    "anjal2utf8",
    "bamini2utf8",
    "boomi2utf8",
    "dinakaran2utf8",
    "dinathanthy2utf8",
    "kavipriya2utf8",
    "murasoli2utf8",
    "mylai2utf8",
    "nakkeeran2utf8",
    "roman2utf8",
    "tab2utf8",
    "tam2utf8",
    "tscii2utf8",
    "indoweb2utf8",
    "koeln2utf8",
    "libi2utf8",
    "oldvikatan2utf8",
    "webulagam2utf8",
    "auto2utf8",
    "dinamani2utf8",
    "pallavar2utf8",
    "diacritic2utf8",
    "shreelipi2utf8",
    "softview2utf8",
    "tace2utf8",
    "vanavil2utf8",
]

__all__ = [
    "ALL_ENCODINGS",
    "encode2unicode",
    "auto2unicode",
    "convert_legacy_to_unicode",
    "auto_detect_encoding",
]


def _normalize_charmap(charmap: OrderedDict) -> OrderedDict:
    """
    Normalizes regex-escaped keys (like '\\$', '\\[', '\\^', '\\/') in encode2utf8 dictionaries
    so literal string replacement works accurately for all characters.
    """
    normalized = OrderedDict()
    for key, val in charmap.items():
        clean_key = (
            key.replace(r"\[", "[")
            .replace(r"\]", "]")
            .replace(r"\$", "$")
            .replace(r"\^", "^")
            .replace(r"\/", "/")
            .replace(r"\+", "+")
            .replace(r"\*", "*")
        )
        normalized[clean_key] = val
        if clean_key != key:
            normalized[key] = val
    return normalized


_all_encodes_ = OrderedDict(
    [
        ("anjal2utf8", _normalize_charmap(anjal2utf8)),
        ("bamini2utf8", _normalize_charmap(bamini2utf8)),
        ("boomi2utf8", _normalize_charmap(boomi2utf8)),
        ("dinakaran2utf8", _normalize_charmap(dinakaran2utf8)),
        ("dinamani2utf8", _normalize_charmap(dinamani2utf8)),
        ("dinathanthy2utf8", _normalize_charmap(dinathanthy2utf8)),
        ("kavipriya2utf8", _normalize_charmap(kavipriya2utf8)),
        ("murasoli2utf8", _normalize_charmap(murasoli2utf8)),
        ("mylai2utf8", _normalize_charmap(mylai2utf8)),
        ("nakkeeran2utf8", _normalize_charmap(nakkeeran2utf8)),
        ("roman2utf8", _normalize_charmap(roman2utf8)),
        ("tab2utf8", _normalize_charmap(tab2utf8)),
        ("tam2utf8", _normalize_charmap(tam2utf8)),
        ("tscii2utf8", _normalize_charmap(tscii2utf8)),
        ("pallavar2utf8", _normalize_charmap(pallavar2utf8)),
        ("indoweb2utf8", _normalize_charmap(indoweb2utf8)),
        ("koeln2utf8", _normalize_charmap(koeln2utf8)),
        ("libi2utf8", _normalize_charmap(libi2utf8)),
        ("oldvikatan2utf8", _normalize_charmap(oldvikatan2utf8)),
        ("webulagam2utf8", _normalize_charmap(webulagam2utf8)),
        ("diacritic2utf8", _normalize_charmap(diacritic2utf8)),
        ("shreelipi2utf8", _normalize_charmap(shreelipi2utf8)),
        ("softview2utf8", _normalize_charmap(softview2utf8)),
        ("tace2utf8", _normalize_charmap(tace2utf8)),
        ("vanavil2utf8", _normalize_charmap(vanavil2utf8)),
    ]
)

# Support common aliases like "bamini2utf2" or "bamini"
_ENCODING_ALIASES = {
    "bamini2utf2": "bamini2utf8",
    "bamini": "bamini2utf8",
    "anjal": "anjal2utf8",
    "tscii": "tscii2utf8",
    "tab": "tab2utf8",
    "tam": "tam2utf8",
    "vanavil": "vanavil2utf8",
}


def resolve_encoding_name(encoding: str = None) -> str:
    if not encoding:
        return None
    enc = encoding.strip().lower()
    if enc in _ENCODING_ALIASES:
        return _ENCODING_ALIASES[enc]
    if enc.endswith("2unicode"):
        enc = enc.replace("2unicode", "2utf8")
    return enc if enc in _all_encodes_ else encoding


def _compute_unique_common_encodes():
    """
    Precomputes unique character sets per encoding and common compound characters
    across all 25 legacy encodings once at module import time.
    """
    all_unique_encodes = []
    all_unicode_encodes = {
        name: set(encode.keys()) for name, encode in _all_encodes_.items()
    }
    all_unique_encodes_full = all_unicode_encodes.copy()
    all_common_encodes = set()

    for supname, super_encode in all_unicode_encodes.items():
        unique_set = set(super_encode)
        for subname, sub_encode in all_unicode_encodes.items():
            if supname != subname:
                unique_set -= sub_encode
        common = all_unique_encodes_full[supname] - unique_set
        all_common_encodes |= common
        all_unique_encodes.append((supname, unique_set))

    # Remove single characters from common compound characters
    all_common_encodes = {ch for ch in all_common_encodes if len(ch) > 1}
    return all_unique_encodes, all_common_encodes


_PRECOMPUTED_UNIQUE_ENCODES, _PRECOMPUTED_COMMON_ENCODES = _compute_unique_common_encodes()


def _get_unique_common_encodes():
    return _PRECOMPUTED_UNIQUE_ENCODES, _PRECOMPUTED_COMMON_ENCODES


def encode2unicode(text, charmap):
    """
    Converts legacy font-encoded text to Tamil Unicode using the specified OrderedDict charmap.
    """
    if isinstance(text, (list, tuple)):
        unitxt = ""
        for line in text:
            for key, val in charmap.items():
                if key in line:
                    line = line.replace(key, val)
            unitxt += line
        return unitxt
    elif isinstance(text, str):
        for key, val in charmap.items():
            if key in text:
                text = text.replace(key, val)
        return text
    return text


def _get_unique_ch(text, all_common_encodes):
    """Extracts unique character sequences from input text outside common compound characters."""
    if isinstance(text, str):
        lines = text.split("\n")
    elif isinstance(text, (list, tuple)):
        lines = text
    else:
        return ""

    special_chars = {".", ",", ";", ":", "", " ", "\r", "\t", "=", "\n"}
    for line in lines:
        for word in line.split(" "):
            for ch in all_common_encodes:
                if ch in word:
                    word = word.replace(ch, "")
            if not word:
                continue
            for ch in list(word):
                if ch.isdigit() or ch in special_chars:
                    word = word.replace(ch, "")
            if word:
                return word
    return ""


def auto_detect_encoding(legacy_text: str) -> str:
    """
    Automatically identifies the legacy Tamil font encoding of the input text.

    Args:
        legacy_text (str): The legacy font-encoded text.

    Returns:
        str: Detected encoding name (e.g. 'bamini2utf8') or 'Unknown'.
    """
    if not legacy_text or not legacy_text.strip():
        return "Unknown"

    # Bamini signature check: In Bamini, ';' is the pulli (்) character attached to
    # consonants (e.g., 'k;'=ம், 'f;'=க், 'j;'=த், 'd;'=ன், 'y;'=ல், 'w;'=ற், 'o;'=ழ்).
    # Because _get_unique_ch strips ';', checking the Bamini pulli pattern first prevents
    # false positives like 'cyfk;' -> 'cyf' matching 'yf' in mylai2utf8.
    import re
    if re.search(r"[fjqrlzjeadkuyshwtobg];", legacy_text):
        return "bamini2utf8"

    unique_chars = _get_unique_ch(legacy_text, _PRECOMPUTED_COMMON_ENCODES)
    if unique_chars:
        for encode_name, encode_keys in _PRECOMPUTED_UNIQUE_ENCODES:
            if not encode_keys:
                continue
            for ch in encode_keys:
                if ch in unique_chars:
                    return encode_name

    if any(
        pat in legacy_text for pat in ("fh", "fp", "nf", "Nf", "jp", "th", "jk", "tz")
    ):
        return "bamini2utf8"

    return "Unknown"


def auto2unicode(text: str) -> str:
    """Automatically detects the legacy encoding and converts the text into Tamil Unicode."""
    detected = auto_detect_encoding(text)
    if detected in _all_encodes_:
        logger.debug(f"Auto-detected legacy encoding '{detected}' for text.")
        return encode2unicode(text, _all_encodes_[detected])
    # Fallback to Bamini if detection was inconclusive
    return encode2unicode(text, _all_encodes_["bamini2utf8"])


def convert_legacy_to_unicode(legacy_text: str, encoding: str = None) -> str:
    """
    Converts legacy Tamil font-encoded text into Tamil Unicode.

    Args:
        legacy_text (str): The legacy font-encoded text.
        encoding (str, optional): Specific encoding name (e.g. 'bamini2utf8').

    Returns:
        str: Converted Tamil Unicode text.
    """
    resolved = resolve_encoding_name(encoding)
    if resolved and resolved in _all_encodes_:
        return encode2unicode(legacy_text, _all_encodes_[resolved])
    return auto2unicode(legacy_text)
