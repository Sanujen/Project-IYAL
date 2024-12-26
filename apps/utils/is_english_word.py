import nltk
from nltk.corpus import words
nltk.download('words')

def is_english_word(word):
    """
    Checks if a given word exists in the English vocabulary.

    Args:
        word: The word to check.

    Returns:
        True if the word is in the English vocabulary, False otherwise.
    """
    english_vocab = set(words.words())
    return word.lower() in english_vocab