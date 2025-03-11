"""
TODO: can we use this instead of googletrans? are these two the same?
# https://translate.google.com/m
from deep_translator import GoogleTranslator

# Use any translator you like, in this example GoogleTranslator
translated = GoogleTranslator(source='en', target='ta').translate("keep it up, you are awesome")  # output -> 'அதை வைத்திருங்கள், நீங்கள் அருமை'

"""
from googletrans import Translator

def translate_english_to_tamil(english_text):
    """
    Translates English text to Tamil.
    translate.googleapis.com is used as the translation service.

    Args:
        english_text (str): The English text to translate.

    Returns:
        str: The translated Tamil text.

    """
    translator = Translator()
    return translator.translate(english_text, src='en', dest='ta').text