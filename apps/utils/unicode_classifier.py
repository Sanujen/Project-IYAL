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
    tamil_characters = range(0x0B80, 0x0BFF + 1)  # Tamil Unicode range
    input_text_unicode_array = [ord(char) for char in input_text]
    contains_tamil = any(char in tamil_characters for char in input_text_unicode_array)
    contains_english = any(char.isascii() and char.isalpha() for char in input_text)
    if contains_tamil and contains_english:
        return "mixed"
    elif contains_tamil:
        return "raw_tamil"
    else:
        return "english"