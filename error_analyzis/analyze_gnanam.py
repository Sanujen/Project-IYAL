import os
import sys
from docx import Document

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from iyal_quality_analyzer.inference_base.inference import Inference
from iyal_quality_analyzer.quality_analyzer import single_sentence_quality_analyzer


def analyze_text_files(directory: str, model: Inference, encoding: str = "bamini2utf8"):
    """
    Analyzes all .txt files in the specified directory using the sentence_quality_analyzer function.

    Args:
        directory (str): The path to the directory containing .txt files.
        model (Inference): The model to use for legacy font classification.
        encoding (str): The encoding of the input text (e.g., bamini2utf8, etc.).
    """
    breakpoint()
    for filename in os.listdir(directory):
        if filename.endswith(".TXT"):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip():  # Skip empty lines
                        try:
                            output, results = single_sentence_quality_analyzer(
                                model, line.strip(), [], encoding)
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
