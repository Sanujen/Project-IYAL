from iyal_quality_analyzer.utils import *
from iyal_quality_analyzer.utils.legacy_converter.legacy_converter import (
    auto_detect_encoding,
)
from iyal_quality_analyzer.inference_base.inference import Inference

__all__ = [
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


def single_word_quality_analyzer(
    model: Inference, input_word: str, word_id: int = 0, encoding: str = None
):
    """
    Normalizes a single word into Raw Tamil Unicode and tags the input type.

    Args:
        model (Inference): The model to use for legacy font classification.
        input_word (str): The input word to normalize.
        encoding (str): The encoding of the input text (e.g., bamini2utf8, etc.).

    Returns:
        dict: A dictionary containing the input type and the normalized output.

    """
    result = {"id": word_id, "inputWord": input_word,
              "inputType": "", "output": ""}
    classification = classify_unicode(input_word)

    if is_special_case(input_word):
        # Special case, leave as is
        result["inputType"] = "special_case"
        result["output"] = input_word

    elif classification == "en_numeric":
        # Mixed English and Numeric, extract the english part, transliterate to Tamil Unicode and add the numeric part again
        result["inputType"] = classification
        en_part = ""
        output = ""
        # if the next char not an en char then transliterate the en_part
        for i, char in enumerate(input_word):
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

    elif classification == "numeric" or classification == "raw_tamil":
        # Numeric or Raw Tamil, leave as is
        result["inputType"] = classification
        result["output"] = input_word

    elif classification == "en_tamil":
        # Mixed Tamil and English, transliterate to Tamil
        result["inputType"] = classification
        result["output"] = transliterate(input_word)

    elif classification == "english":
        # Could be English or Romanized Tamil or Legacy Tamil
        # Check if it's English word by a simple check with corpus
        if is_english_word(input_word):
            # English word, leave as is for now
            result["inputType"] = classification
            result["output"] = input_word

        else:
            # Could be Romanized Tamil or Legacy Tamil
            # Using a classifier model to determine the type whether Romanized or Legacy
            input_type = model.inference(input_word)
            result["inputType"] = input_type
            if input_type == "Romanized Text Encoding":
                # Romanized Tamil, transliterate to Tamil Unicode
                result["output"] = transliterate(input_word)

            elif input_type == "Legacy Font Encoding":
                # Legacy Tamil, convert to Tamil Unicode
                result["output"] = convert_legacy_to_unicode(
                    input_word, encoding)

            else:
                # handle other cases
                result["output"] = "unknown"
    else:
        result["inputType"] = "unknown"
        result["output"] = input_word

    return result


def sentence_quality_analyzer(
    model: Inference,
    input_text: str,
    encoding: str = None,
    need_translation: bool = False,
):
    return single_sentence_quality_analyzer(
        model, input_text, [], encoding, need_translation
    )


def single_sentence_quality_analyzer(
    classifier: Inference,
    coll_to_stand: Inference,
    input_text: str,
    results: list,
    encoding: str = None,
    need_translation: bool = False,
    colloquial_to_standard: bool = False,
):
    """
    Normalizes a block of text into Raw Tamil Unicode and tags the input type.

    Args:
        Model (Inference): The model to use for legacy font classification.
        input_text (str): The input text to normalize.
        encoding (str): The encoding of the input text (e.g., bamini2utf8, etc.).

    Returns:
        tuple: A tuple containing the normalized output and a list of single-word
        quality analysis results.

    """
    output_text = ""
    words = input_text.split()
    word_id = len(results)
    for word in words:
        result = single_word_quality_analyzer(
            classifier, word, word_id, encoding)
        results.append(result)
        word_id += 1

    if need_translation:
        final_results = []
        to_be_translated = []
        transalted_ids = []

        for i, result in enumerate(results):
            if result["inputType"] == "english":
                to_be_translated.append(result["output"])
                transalted_ids.append(result["id"])

                if i + 1 < len(results) and results[i + 1]["inputType"] == "en":
                    continue

                to_be_translated_text = " ".join(to_be_translated)
                translated_text = translate_english_to_tamil(
                    to_be_translated_text)
                if len(transalted_ids) > 1:
                    id_range = transalted_ids[0], transalted_ids[-1]
                else:
                    id_range = transalted_ids[0]
                final_results.append(
                    {
                        "id": id_range,
                        "inputWord": to_be_translated_text,
                        "inputType": "english",
                        "output": translated_text,
                    }
                )
                to_be_translated = []
                transalted_ids = []
            else:
                final_results.append(result)
    else:
        final_results = results

    output_text = " ".join([result["output"] for result in final_results])

    if colloquial_to_standard:
        output_text = coll_to_stand.inference(output_text)

    return (output_text.strip(), final_results)


def multi_sentence_quality_analyzer(
    classifier: Inference, coll_to_stand: Inference, input_text: str, encoding: str = None, need_translation: bool = False, colloquial_to_standard: bool = False
):
    """
    Normalizes a block of text into Raw Tamil Unicode and tags the input type.

    Args:
        model (Inference): The model to use for legacy font classification.
        input_text (str): The input text to normalize.
        encoding (str): The encoding of the input text (e.g., bamini2utf8, etc.).
        need_translation (bool): Flag to indicate if translation is needed.

    Returns:
        tuple: A tuple containing the normalized output and a list of sentence
        quality analysis results.

    """
    output_text = ""

    sentences = sentence_segmentation(input_text)
    sentence_results = []
    for sentence in sentences:
        results = []
        output, sentence_result = single_sentence_quality_analyzer(
            classifier, coll_to_stand, sentence, results, encoding, need_translation, colloquial_to_standard
        )
        output_text += output + " "
        if sentence_result:
            sentence_results.append(
                {"sentence": sentence, "results": sentence_result})

    return (output_text.strip(), sentence_results)


def sentence_segmentation(input_text: str):
    """
    Segment the input text into sentences. This function is a simple sentence segmentation
    algorithm that splits the input text based on punctuation marks.

    Args:
        input_text (str): The input text to segment.

    Returns:
        list: A list of segmented sentences

    """
    # Define punctuation marks and wrapper marks
    punctuation_marks = [".", "?", "!"]
    wrapper_in_marks = ["\"", "(", "[", "{"]
    wrapper_out_marks = ["\"", ")", "]", "}"]

    temp = ''
    sentences = []
    check = 0
    for char in input_text:
        if char in wrapper_in_marks:
            check += 1
        elif char in wrapper_out_marks:
            check -= 1

        if char in punctuation_marks and check == 0:
            if temp.strip():
                sentences.append(temp.strip())
            temp = ''
        else:
            temp += char

    if temp.strip():
        sentences.append(temp.strip())

    return sentences


def get_encoding_fun(model: Inference, input_text: str):
    """
    Detects the encoding of the input text.

    Args:
        model (Inference): The model to use for legacy font classification.
        input_text (str): The input text to analyze.

    Returns:
        str: The detected encoding.

    """
    words = input_text.split()

    for word in words:
        classification = classify_unicode(word)

        if classification == "english" and not is_english_word(word):
            input_type = model.inference(word)
            if input_type == "Legacy Font Encoding":
                font_style = auto_detect_encoding(word)
                if font_style in __all__:
                    return font_style
