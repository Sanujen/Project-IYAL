def transliterate(input_text):
    """
    # TODO: Use an API for transliteration (So far we planned to use an google API)
    Transliterates Tamil Romanized text into Tamil Unicode.

    Args:
        input_text (str): The Romanized Tamil text to transliterate.

    Returns:
        str: Transliterated Tamil Unicode text.
    """
    transliteration_map = {
        "ka": "\u0B95",
        "na": "\u0BA8",
        # Add more mappings...
    }

    output_text = ""
    words = input_text.split()
    for word in words:
        output_text += transliteration_map.get(word, word) + " "

    return output_text.strip()