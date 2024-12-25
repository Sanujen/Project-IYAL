from apps.utils import *
from apps.inference_base.inference import Inference

def handle_mixed_input(input_word: str):
    """
    Processes mixed Tamil and English input by transliterating English parts
    and preserving Tamil Unicode parts.

    Args:
        input_word (str): Mixed input containing Tamil and English text.

    Returns:
        str: Fully normalized Tamil Unicode text.
    """
    tamil_characters = set("\u0B80-\u0BFF")  # Tamil Unicode range
    output_text = ""

    for char in input_word:
        if char in tamil_characters:
            # Preserve Tamil characters
            output_text += char
        elif char.isascii() and char.isalpha():
            # Transliterate English characters
            output_text += transliterate(char)
        else:
            # Preserve non-alphabetic characters (e.g., punctuation)
            output_text += char

    return output_text

def single_word_quality_analyzer(model: Inference, input_word: str, encoding: str = None):
    """
    Normalizes a single word into Raw Tamil Unicode and tags the input type.

    Args:
        model (Inference): The model to use for legacy font classification.
        input_word (str): The input word to normalize.
        encoding (str): The encoding of the input text (e.g., bamini2utf8, etc.).

    Returns:
        dict: A dictionary containing the input type and the normalized output.

    """
    result = {
        "inputType": "",
        "output": ""
    }
    classification = classify_unicode(input_word)

    if classification == "raw_tamil":
        # Already normalized, return as is
        result["inputType"] = "raw_tamil"
        result["output"] = input_word

    elif classification == "mixed":
        # Mixed input isn't possible for single-word input
        result["inputType"] = "mixed"
        result["output"] = handle_mixed_input(input_word)

    elif classification == "english":
        # Could be English or Romanized Tamil or Legacy Tamil
        # Check if it's English word by a simple check with corpus
        if is_english_word(input_word):
            # English word, translate to Tamil
            result["inputType"] = "en"
            result["output"] = translate_english_to_tamil(input_word)

        else:
            # Could be Romanized Tamil or Legacy Tamil
            # Using a classifier model to determine the type whether Romanized or Legacy
            input_type = model.inference(input_word)
            result["inputType"] = input_type
            if input_type == "romanized":
                # Romanized Tamil, transliterate to Tamil Unicode
                result["output"] = transliterate(input_word)

            elif input_type == "legacy":
                # Legacy Tamil, convert to Tamil Unicode
                result["output"] = convert_legacy_to_unicode(input_word, encoding)

            else:
                # handle other cases
                result["output"] = "unknown"
    
    return result
    
def quality_analyzer(model: Inference, input_text: str, encoding: str = None):
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
    results = []
    for word in words:
        result = single_word_quality_analyzer(model, word, encoding)
        results.append(result)
        output_text += result["output"] + " "

    return (output_text.strip(), results)