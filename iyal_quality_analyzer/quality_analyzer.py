'''
TODO:
    - Add a function to handle multiple sentences by adding sentence segmentation
    - Add a function to only get the texts which are in legacy font, and then call the function for the legacy font detection which should be available in legacy_converter.py. This function only returns the encoding of the given text.
    - Add a warning in the docstring of the quality_analyzer function saying that if the user selects auto-detect for the legacy font, can't be sure about the accuracy of the result.
    - After finding the english words, before transliterating the text, us RE to ignore special cases like words within quotes, brackets, etc.
        - Also refine `output_text = translate_english_to_tamil(output_text)` to handle these special cases. (cuz the current implementation will translate the words within quotes, brackets, etc. as well)
        - Also, map the inputType as <something> for these special cases.

'''

from iyal_quality_analyzer.utils import *
from iyal_quality_analyzer.inference_base.inference import Inference

def single_word_quality_analyzer(model: Inference, input_word: str, word_id: int, encoding: str = None):
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
        "id": word_id,
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
        # Mixed Tamil and English, transliterate to Tamil
        result["inputType"] = "mixed"
        result["output"] = transliterate(input_word)

    elif classification == "english":
        # Could be English or Romanized Tamil or Legacy Tamil
        # Check if it's English word by a simple check with corpus
        if is_english_word(input_word):
            # English word, translate to Tamil
            result["inputType"] = "en"
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
                result["output"] = convert_legacy_to_unicode(input_word, encoding)

            else:
                # handle other cases
                result["output"] = "unknown"
    
    return result
    
def single_sentence_quality_analyzer(model: Inference, input_text: str, results: list, encoding: str = None):
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
        result = single_word_quality_analyzer(model, word, word_id, encoding)
        results.append(result)
        output_text += result["output"] + " "

    # Check the results arrays. If there's one or more objects with 'en' inputType, then the whole text needed to translate
    # to Tamil. Otherwise, the text is already in Tamil and doesn't need further translation.
    if any(result["inputType"] == "en" for result in results):
        output_text = translate_english_to_tamil(output_text)
    # TODO: after this translation, need to leave the input word as it is for output by looking the inputType.

    return (output_text.strip(), results)

def multi_sentence_quality_analyzer(model: Inference, input_text: str, encoding: str = None):
    output_text = ""
    results = []

    sentences = sentence_segmentation(input_text)
    for sentence in sentences:
        output, results = single_sentence_quality_analyzer(model, sentence, results, encoding)
        output_text += output + " "
    
    return (output_text.strip(), results)

def sentence_segmentation(input_text: str):
    pass