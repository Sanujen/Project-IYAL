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
from iyal_quality_analyzer.utils.legacy_converter.legacy_converter import auto_detect_encoding
from iyal_quality_analyzer.inference_base.inference import Inference
import stanza
import csv
import os

import requests

def convert_bamini_to_unicode(input_word: str) -> str:
    url = "https://api.ezhil.ai/v1/convert"
    payload = {
        "text": input_word,
        "from": "bamini",
        "to": "unicode"
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_API_KEY"  # Replace with your Ezhil API key
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("converted_text", "")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

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

def update_csv(input_word: str, input_type: str, output: str, actual_output: str, csv_file: str = 'E:\___MORA\FYP\FinalRepos\Project-IYAL\error_analyzis\output.csv'):
    """
    Updates the CSV file with the given data.

    Args:
        input_word (str): The input word.
        input_type (str): The input type.
        output (str): The output.
        actual_output (str): The actual output.
        csv_file (str): The path to the CSV file.
    """
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writerow(['inputWord', 'inputType', 'output', 'actualOutput'])
        writer.writerow([input_word, input_type, output, actual_output])

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

    if is_special_case(input_word):
        # Special case, leave as is
        result["inputType"] = "special_case"
        result["output"] = input_word

    elif classification == "raw_tamil":
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
                result["output"] = convert_legacy_to_unicode(
                    input_word, encoding)

            else:
                # handle other cases
                result["output"] = "unknown"

    # Calculate actual output
    breakpoint()
    actual_output = convert_bamini_to_unicode(input_word)

    # Update CSV file
    update_csv(input_word, result["inputType"], result["output"], actual_output)

    return result

def sentence_quality_analyzer(model: Inference, input_text: str, encoding: str = None):
    return single_sentence_quality_analyzer(model, input_text, [], encoding)

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
        word_id += 1

    final_results = []
    to_be_translated = []
    transalted_ids = []

    for i, result in enumerate(results):
        if result["inputType"] == "en":
            to_be_translated.append(result["output"])
            transalted_ids.append(result["id"])

            if i + 1 < len(results) and results[i + 1]["inputType"] == "en":
                continue
            
            to_be_translated_text = " ".join(to_be_translated)
            translated_text = translate_english_to_tamil(to_be_translated_text)
            if len(transalted_ids) > 1:
                id_range = transalted_ids[0], transalted_ids[-1]
            else:
                id_range = transalted_ids[0]
            final_results.append({
                "id": id_range,
                "inputWord": to_be_translated_text,
                "inputType": "en",
                "output": translated_text
            })
            to_be_translated = []
            transalted_ids = []
        else:
            final_results.append(result)

    output_text = " ".join([result["output"] for result in final_results])
    
    return (output_text.strip(), final_results)

def multi_sentence_quality_analyzer(model: Inference, input_text: str, encoding: str = None):
    output_text = ""
    results = []

    sentences = sentence_segmentation(input_text)
    sentence_results = []
    for sentence in sentences:
        output, sentence_result = single_sentence_quality_analyzer(
            model, sentence, results, encoding)
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


def get_encoding_fun(model: Inference, input_text: str):
    words = input_text.split()

    for word in words:
        classification = classify_unicode(word)

        if classification == "english" and not is_english_word(word):
            input_type = model.inference(word)
            if input_type == "Legacy Font Encoding":
                font_style = auto_detect_encoding(word)
                if font_style in __all__:
                    return font_style
    