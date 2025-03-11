# TODO: Can we change the existing transliteration method to the one below?

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

# import requests

# def transliterate(english_text):
#     url = "https://inputtools.google.com/request"
#     params = {
#         'text': english_text,
#         'itc': 'ta-t-i0-und',
#         'num': 13,
#         'cp': 0,
#         'cs': 0,
#         'ie': 'utf-8',
#         'oe': 'utf-8'
#     }

#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status() 

#         data = response.json()
#         # print(data)
#         if data[0] == 'SUCCESS':
#             return 0, data[1][0][1][0]
#         else:
#             return 1, ''
#     except requests.exceptions.RequestException as e:
#         print(f"Error requesting transliteration: {e}")
#         return 1, ''