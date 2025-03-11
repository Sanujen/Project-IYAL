# https://translate.google.com/m
# https://pypi.org/project/deep-translator/
from deep_translator import GoogleTranslator

# Use any translator you like, in this example GoogleTranslator
translated = GoogleTranslator(source='en', target='ta').translate("keep it up, you are awesome")  # output -> 'அதை வைத்திருங்கள், நீங்கள் அருமை'