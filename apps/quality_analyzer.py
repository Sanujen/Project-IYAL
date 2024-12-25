from apps.utils import *
from apps.inference_base.inference import Inference

def single_word_quality_analyzer(model: Inference, input_word: str, encoding: str = None):
    """
    TODO: function for finding the english word
    Normalizes a single word into Raw Tamil Unicode and tags the input type.

    Args:
        model (Inference): The model to use for legacy font classification.
        input_word (str): The input word to normalize.
        encoding (str): The encoding of the input text (e.g., bamini2utf8, etc.).

    Returns:
        dict: A dictionary containing the input type and the normalized output.

    """
    result = {
        "inputWord": input_word,
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
        result["output"] = transliterate(input_word)

    elif classification == "english":
        # Could be English or Romanized Tamil or Legacy Tamil
        # Check if it's English word by a simple check with corpus
        if not (input_word):
            # English word, translate to Tamil
            result["inputType"] = "en"
            result["output"] = translate_english_to_tamil(input_word)

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