def translate_english_to_tamil(english_text):
    """
    TODO: Use an API for translation (So far we planned to use an google API)
    Translates English words into Tamil.

    Args:
        english_text (str): The English text to translate.

    Returns:
        str: Translated Tamil text.
    """
    english_to_tamil_dict = {
        "hello": "\u0B90",  # Example mapping for "hello"
        "world": "\u0BA9",
        # Add more mappings...
    }

    words = english_text.split()
    translated_text = " ".join(english_to_tamil_dict.get(word, word) for word in words)

    return translated_text