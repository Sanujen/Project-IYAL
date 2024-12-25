from googletrans import Translator

def translate_english_to_tamil(english_text):
    """
    Translates English text to Tamil.

    Args:
        english_text (str): The English text to translate.

    Returns:
        str: The translated Tamil text.

    """
    translator = Translator()
    return translator.translate(english_text, src='en', dest='ta').text