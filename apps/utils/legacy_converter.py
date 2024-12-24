def convert_legacy_to_unicode(legacy_text):
    """
    TODO: implement the algorithm to convert legacy Tamil font-encoded text into Unicode.
    Converts legacy Tamil font-encoded text into Unicode.

    Args:
        legacy_text (str): The legacy font-encoded text.

    Returns:
        str: Converted Unicode text.
    """
    legacy_to_unicode_map = {
        "fw;g": "\u0B95",  # Example mapping for legacy font
        "jhu;": "\u0BA8",
        # Add more mappings...
    }

    unicode_text = ""
    for char in legacy_text:
        unicode_text += legacy_to_unicode_map.get(char, char)

    return unicode_text