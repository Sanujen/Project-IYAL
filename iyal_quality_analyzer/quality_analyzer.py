import re
from typing import Iterable, List, Optional, Tuple
from iyal_quality_analyzer.utils import (
    classify_unicode,
    transliterate,
    convert_legacy_to_unicode,
    auto_detect_encoding,
    ALL_ENCODINGS,
    translate_english_to_tamil,
    is_english_word,
    is_protected_word,
    is_special_case,
)
from iyal_quality_analyzer.inference_base.inference import Inference
from iyal_quality_analyzer.inference_base.inference_coll_to_stand import (
    Inference as CollToStandInference,
)
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.quality_analyzer")

__all__ = ALL_ENCODINGS


def single_word_quality_analyzer(
    model: Inference,
    input_word: str,
    word_id: int = 0,
    encoding: str = None,
    protected_words: Optional[Iterable[str]] = None,
) -> dict:
    """
    Normalizes a single token into Raw Tamil Unicode and tags its classification type
    according to the Project IYAL 11-step word processing flow.

    Args:
        model (Inference): Classifier model for distinguishing Legacy vs. Romanized tokens.
        input_word (str): The token to analyze and normalize.
        word_id (int): Sequential token ID within the sentence.
        encoding (str, optional): Confirmed legacy font encoding (e.g., 'bamini2utf8').
        protected_words (Optional[Iterable[str]]): User/admin custom corpus words not to transliterate/translate.

    Returns:
        dict: {
            "id": int,
            "inputWord": str,
            "unicodeCategory": str,
            "inputType": str,
            "output": str,
            "protected": bool
        }
    """
    result = {
        "id": word_id,
        "inputWord": input_word,
        "unicodeCategory": "",
        "inputType": "",
        "output": "",
        "protected": False,
    }

    classification = classify_unicode(input_word)
    result["unicodeCategory"] = classification

    # 1. Special case check (URLs, emails, phone numbers, [bracketed] tags)
    if is_special_case(input_word):
        result["inputType"] = "special_case"
        result["output"] = input_word
        return result

    # 2. Check User / Admin Protected Corpus first (never transliterate or translate)
    if is_protected_word(input_word, protected_words):
        result["inputType"] = "protected_en"
        result["output"] = input_word
        result["protected"] = True
        return result

    # 3. Alphanumeric mixed token (e.g., 'chennai28')
    if classification == "en_numeric":
        result["inputType"] = "en_numeric"
        en_part = ""
        output = ""
        for char in input_word:
            if char.isalpha():
                en_part += char
            else:
                if en_part:
                    output += transliterate(en_part)
                    en_part = ""
                output += char
        if en_part:
            output += transliterate(en_part)
        result["output"] = output
        return result

    # 4. Pure Numeric or Raw Tamil Unicode — leave as-is
    if classification in ("numeric", "raw_tamil"):
        result["inputType"] = classification
        result["output"] = input_word
        return result

    # 5. Mixed Tamil + English Unicode (e.g., 'வணkkam') — transliterate to Tamil
    if classification == "en_tamil":
        result["inputType"] = "en_tamil"
        result["output"] = transliterate(input_word)
        return result

    # 6. Non-Tamil Unicode ('english' script range: could be English, Legacy Tamil, or Romanized Tamil)
    if classification == "english":
        if is_english_word(input_word, protected_words):
            result["inputType"] = "en"
            result["output"] = input_word
        else:
            # Classify via Model 1 (Legacy Font Encoding vs. Romanized Text Encoding)
            input_type = model.inference(input_word) if model else "Romanized Text Encoding"
            result["inputType"] = input_type
            if input_type == "Romanized Text Encoding":
                result["output"] = transliterate(input_word)
            elif input_type == "Legacy Font Encoding":
                effective_encoding = (
                    encoding
                    if (encoding and encoding != "legacy_font_not_found")
                    else None
                )
                result["output"] = convert_legacy_to_unicode(input_word, effective_encoding)
            else:
                result["output"] = input_word
        return result

    result["inputType"] = "unknown"
    result["output"] = input_word
    return result


def single_sentence_quality_analyzer(
    classifier: Inference,
    coll_to_stand: Optional[CollToStandInference],
    input_text: str,
    results: list,
    encoding: str = None,
    need_translation: bool = False,
    colloquial_to_standard: bool = False,
    protected_words: Optional[Iterable[str]] = None,
) -> Tuple[str, list]:
    """
    Normalizes a single sentence into Tamil Unicode, optionally translating English phrases
    and standardizing colloquial Tamil via the mBART standardizer.
    """
    words = input_text.split()
    word_id = len(results)
    for word in words:
        res = single_word_quality_analyzer(
            classifier, word, word_id, encoding, protected_words=protected_words
        )
        results.append(res)
        word_id += 1

    # Step 10: Optional translation of English words (skipping user-protected words!)
    if need_translation:
        final_results = []
        to_be_translated = []
        translated_ids = []

        for i, res in enumerate(results):
            if res["inputType"] == "en" and not res.get("protected", False):
                to_be_translated.append(res["output"])
                translated_ids.append(res["id"])

                if (
                    i + 1 < len(results)
                    and results[i + 1]["inputType"] == "en"
                    and not results[i + 1].get("protected", False)
                ):
                    continue

                phrase = " ".join(to_be_translated)
                translated_text = translate_english_to_tamil(phrase)
                id_range = (
                    (translated_ids[0], translated_ids[-1])
                    if len(translated_ids) > 1
                    else translated_ids[0]
                )
                final_results.append(
                    {
                        "id": id_range,
                        "inputWord": phrase,
                        "unicodeCategory": "english",
                        "inputType": "en_translated",
                        "output": translated_text,
                        "protected": False,
                    }
                )
                to_be_translated = []
                translated_ids = []
            else:
                final_results.append(res)
    else:
        final_results = results

    output_text = " ".join([r["output"] for r in final_results]).strip()

    # Step 11: Optional Colloquial-to-Standard Tamil standardization
    if colloquial_to_standard and coll_to_stand is not None and output_text:
        output_text = coll_to_stand.inference(output_text)

    return output_text.strip(), final_results


def multi_sentence_quality_analyzer(
    classifier: Inference,
    coll_to_stand: Optional[CollToStandInference],
    input_text: str,
    encoding: str = None,
    need_translation: bool = False,
    colloquial_to_standard: bool = False,
    protected_words: Optional[Iterable[str]] = None,
) -> Tuple[str, list]:
    """
    Segments a multi-sentence paragraph, processes each sentence word-by-word through
    the normalization pipeline, and reconstructs the normalized paragraph.
    """
    if not input_text or not input_text.strip():
        return "", []

    segmented_sentences = sentence_segmentation(input_text)
    sentence_results = []
    output_parts = []

    for segment in segmented_sentences:
        results = []
        raw_sentence = segment["sentence"]
        punctuation = segment["punctuation"]

        # First get pre-standardized output if colloquial_to_standard is requested, so UI can show both
        output, sentence_tokens = single_sentence_quality_analyzer(
            classifier,
            coll_to_stand,
            raw_sentence,
            results,
            encoding=encoding,
            need_translation=need_translation,
            colloquial_to_standard=colloquial_to_standard,
            protected_words=protected_words,
        )

        pre_standardized = " ".join([r["output"] for r in sentence_tokens]).strip()
        full_sentence_out = f"{output}{punctuation}".strip()
        output_parts.append(full_sentence_out)

        if sentence_tokens:
            sentence_results.append(
                {
                    "input_sentence": f"{raw_sentence}{punctuation}".strip(),
                    "pre_standardized_sentence": f"{pre_standardized}{punctuation}".strip(),
                    "output_sentence": full_sentence_out,
                    "standardized_applied": bool(colloquial_to_standard),
                    "results": sentence_tokens,
                }
            )

    return " ".join(output_parts).strip(), sentence_results


def quality_analyzer(
    classifier: Inference,
    input_text: str,
    encoding: str = None,
    need_translation: bool = False,
    colloquial_to_standard: bool = False,
    coll_to_stand: Optional[CollToStandInference] = None,
    protected_words: Optional[Iterable[str]] = None,
) -> Tuple[str, list]:
    """Convenience wrapper matching the package README signature."""
    return multi_sentence_quality_analyzer(
        classifier=classifier,
        coll_to_stand=coll_to_stand,
        input_text=input_text,
        encoding=encoding,
        need_translation=need_translation,
        colloquial_to_standard=colloquial_to_standard,
        protected_words=protected_words,
    )


def sentence_segmentation(input_text: str) -> List[dict]:
    """
    Segments input text into sentences while preserving email addresses, URLs,
    and parenthetical/bracketed expressions.
    """
    punctuation_marks = {".", "?", "!"}
    wrapper_in_marks = {'"', "(", "[", "{"}
    wrapper_out_marks = {'"', ")", "]", "}"}

    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    url_pattern = re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+")

    temp = ""
    sentences = []
    check = 0
    i = 0
    n = len(input_text)

    while i < n:
        char = input_text[i]

        if char == ".":
            start_idx = max(0, i - 25)
            end_idx = min(n, i + 25)
            look_ahead = input_text[start_idx:end_idx]
            if email_pattern.search(look_ahead) or url_pattern.search(look_ahead):
                temp += char
                i += 1
                continue

        if char in wrapper_in_marks:
            check += 1
        elif char in wrapper_out_marks and check > 0:
            check -= 1

        if char in punctuation_marks and check == 0:
            if temp.strip():
                sentences.append({"sentence": temp.strip(), "punctuation": char})
            temp = ""
        else:
            temp += char
        i += 1

    if temp.strip():
        stripped = temp.strip()
        last_char = stripped[-1]
        if last_char in punctuation_marks:
            sentences.append({"sentence": stripped[:-1].strip(), "punctuation": last_char})
        else:
            sentences.append({"sentence": stripped, "punctuation": ""})

    return sentences


def detect_legacy_encoding_details(
    model: Inference,
    input_text: str,
    protected_words: Optional[Iterable[str]] = None,
) -> dict:
    """
    Scans the input text for non-English tokens classified as 'Legacy Font Encoding',
    identifies the legacy font via auto_detect_encoding, and returns sample previews
    for UI confirmation (Step 7 of the domain pipeline).
    """
    words = input_text.split()
    detected_font = None
    legacy_words = []

    for word in words:
        if is_special_case(word) or is_protected_word(word, protected_words):
            continue
        classification = classify_unicode(word)
        if classification == "english" and not is_english_word(word, protected_words):
            input_type = model.inference(word) if model else "Romanized Text Encoding"
            if input_type == "Legacy Font Encoding":
                legacy_words.append(word)
                if not detected_font:
                    candidate = auto_detect_encoding(word)
                    if candidate in ALL_ENCODINGS:
                        detected_font = candidate

    if not detected_font and legacy_words:
        # Try detecting across all legacy words combined
        combined_candidate = auto_detect_encoding(" ".join(legacy_words))
        detected_font = (
            combined_candidate if combined_candidate in ALL_ENCODINGS else "bamini2utf8"
        )

    if not detected_font:
        return {
            "encoding": "legacy_font_not_found",
            "requires_confirmation": False,
            "legacy_samples": [],
        }

    # Build up to 5 sample previews for the user confirmation dialog in UI
    seen = set()
    samples = []
    for w in legacy_words:
        if w not in seen:
            seen.add(w)
            samples.append(
                {
                    "word": w,
                    "preview_unicode": convert_legacy_to_unicode(w, detected_font),
                }
            )
            if len(samples) >= 5:
                break

    return {
        "encoding": detected_font,
        "requires_confirmation": True,
        "legacy_samples": samples,
    }


def get_encoding_fun(
    model: Inference,
    input_text: str,
    protected_words: Optional[Iterable[str]] = None,
) -> str:
    """
    Detects the legacy font encoding of the input text.
    Returns 'legacy_font_not_found' if no legacy font tokens are detected.
    """
    details = detect_legacy_encoding_details(
        model, input_text, protected_words=protected_words
    )
    return details["encoding"]
