import os
import sys
from docx import Document
import csv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from iyal_quality_analyzer.inference_base.inference import Inference
from iyal_quality_analyzer.quality_analyzer import single_sentence_quality_analyzer
from iyal_quality_analyzer.utils.legacy_converter.legacy_converter import convert_legacy_to_unicode

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

def analyze_text_files(directory: str, model: Inference, encoding: str = "bamini2utf8"):
    """
    Analyzes all .txt files in the specified directory using the sentence_quality_analyzer function.

    Args:
        directory (str): The path to the directory containing .txt files.
        model (Inference): The model to use for legacy font classification.
        encoding (str): The encoding of the input text (e.g., bamini2utf8, etc.).
    """
    for filename in os.listdir(directory):
        if filename.endswith(".TXT"):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip():  # Skip empty lines
                        try:
                            output, results = single_sentence_quality_analyzer(
                                model, line.strip(), [], encoding)
                                # Calculate actual output

                            # Update CSV file
                            for result in results:
                                input_word = result["inputWord"]
                                actual_output = convert_legacy_to_unicode(input_word, 'bamini2utf8')
                                update_csv(input_word, result["inputType"], result["output"], actual_output)
                                    
                        except Exception as e:
                            print(f"Error processing line: {str(e)}")
                            continue
        elif filename.endswith(".docx"):
            file_path = os.path.join(directory, filename)
            document = Document(file_path)
            for paragraph in document.paragraphs:
                line = paragraph.text.strip()
                if line:  # Skip empty lines
                    try:
                        output, results = single_sentence_quality_analyzer(
                            model, line, [], encoding)
                        
                        for result in results:
                            input_word = result["inputWord"]
                            actual_output = convert_legacy_to_unicode(input_word, 'bamini2utf8')
                            update_csv(input_word, result["inputType"], result["output"], actual_output)
                    except Exception as e:
                        print(f"Error processing line: {str(e)}")
                        continue


if __name__ == "__main__":
    # Redirect stdout and stderr to os.devnull to suppress all output except the print statement inside the Exception block
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    directory = 'E:\___MORA\FYP\gnanm\gnanamp65Files\G-01'
    model = Inference()  # Initialize your model here
    analyze_text_files(directory, model)
