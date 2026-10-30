def classify_unicode(input_text: str) -> str:
    """
    Classifies a token into its primary Unicode script category:
    - 'raw_tamil': Pure Tamil Unicode characters (U+0B80..U+0BFF)
    - 'en_tamil': Mixed Tamil Unicode + ASCII/Latin characters
    - 'en_numeric': Mixed ASCII/Latin characters + digits
    - 'numeric': Digits only
    - 'english': Non-Tamil Unicode (ASCII/Latin script — may be English, Romanized Tamil, or Legacy Font)

    Args:
        input_text (str): The input token to classify.

    Returns:
        str: Classification category ('raw_tamil', 'en_tamil', 'en_numeric', 'numeric', 'english').
    """
    tamil_range = range(0x0B80, 0x0BFF + 1)
    contains_tamil = any(ord(ch) in tamil_range for ch in input_text)
    contains_english = any(ch.isascii() and ch.isalpha() for ch in input_text)
    contains_numeric = any(ch.isdigit() for ch in input_text)

    if contains_tamil and contains_english:
        return "en_tamil"
    elif contains_tamil:
        return "raw_tamil"
    elif contains_english and contains_numeric:
        return "en_numeric"
    elif contains_numeric and not contains_english:
        return "numeric"
    else:
        return "english"
