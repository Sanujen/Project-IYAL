from google.transliteration import transliterate_text

def transliterate(input_text):
    """
    Transliterate the input text to Tamil Unicode.

    Args:
        input_text (str): The input text to transliterate.

    Returns:
        str: The transliterated Tamil Unicode text.

    """
    return transliterate_text(input_text, lang_code='ta')
