def classify_unicode(input_text):
    """
    Classifies input text into categories:
    - Raw Tamil Unicode
    - Tamil + English Unicode
    - English Unicode

    Args:
        input_text (str): The input text to classify.

    Returns:
        str: Classification type ('raw_tamil', 'mixed', 'english')
    """
    tamil_characters = set("\u0B80-\u0BFF")  # Tamil Unicode range
    contains_tamil = any(char in tamil_characters for char in input_text)
    contains_english = any(char.isascii() for char in input_text)

    if contains_tamil and contains_english:
        return "mixed"
    elif contains_tamil:
        return "raw_tamil"
    else:
        return "english"