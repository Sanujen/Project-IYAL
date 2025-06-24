import nltk
from nltk.corpus import words
from nltk.data import find


def is_english_word(word, remove_words=['la']):
    """
    Checks if a given word exists in the English vocabulary.

    Args:
        word: The word to check.

    Returns:
        True if the word is in the English vocabulary, False otherwise.
    """
    try:
        find('corpora/words.zip')
    except LookupError:
        nltk.download('words')
    english_vocab = set(words.words())
    for word in remove_words:
        english_vocab.remove(word)
    return word.lower() in english_vocab