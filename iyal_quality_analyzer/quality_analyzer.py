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
import stanza

def single_word_quality_analyzer(model: Inference, input_word: str, word_id: int = 0, encoding: str = None):
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
            # English word, leave as is for now
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
        word_id += 1

    if any(result["inputType"] == "en" for result in results):
        output_text = translate_english_to_tamil(output_text)

    translated_words = output_text.split()
    mapped_results = []
    translated_index = 0
    original_word_buffer = []
    translated_word_buffer = []
    id_buffer = []

    for result in results:
        if result["inputType"] == "en":
            original_word_buffer.append(result["inputWord"])
            translated_word_buffer.append(translated_words[translated_index])
            id_buffer.append(result["id"])
            translated_index += 1

            # Check the next word
            next_result_index = results.index(result) + 1
            if next_result_index < len(results) and results[next_result_index]["inputType"] == "en":
                continue

            # Map the buffered original words to the buffered translated words
            mapped_results.append({
                "id_range": f"{id_buffer[0]}-{id_buffer[-1]}",
                "inputWord": " ".join(original_word_buffer),
                "inputType": "english",
                "output": " ".join(translated_word_buffer)
            })
            original_word_buffer = []
            translated_word_buffer = []
            id_buffer = []
        else:
            mapped_results.append(result)

    # Handle any remaining buffered words
    if original_word_buffer:
        mapped_results.append({
            "id_range": f"{id_buffer[0]}-{id_buffer[-1]}",
            "inputWord": " ".join(original_word_buffer),
            "inputType": "english",
            "output": " ".join(translated_word_buffer)
        })

    output_result = " ".join([result["output"] for result in mapped_results])

    return (output_text.strip(), mapped_results)

def multi_sentence_quality_analyzer(model: Inference, input_text: str, encoding: str = None):
    output_text = ""
    results = []

    sentences = sentence_segmentation(input_text)
    sentence_results = []
    for sentence in sentences:
        output, sentence_result = single_sentence_quality_analyzer(model, sentence, results, encoding)
        output_text += output + " "
        sentence_results.append({
            "sentence": sentence,
            "results": sentence_result
        })
    
    return (output_text.strip(), sentence_results)

def sentence_segmentation(input_text: str):
    nlp = stanza.Pipeline(lang='ta', processors='tokenize')
    doc = nlp(input_text)
    # return input_text.split(".")
    return [sentence.text for sentence in doc.sentences]

