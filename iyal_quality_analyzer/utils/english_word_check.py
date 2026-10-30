from typing import Iterable, Optional, Set
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.english_check")

# Cached English vocabulary set initialized lazily once
_ENGLISH_VOCAB: Optional[Set[str]] = None

# Global protected words synchronized from database / admin settings
_GLOBAL_PROTECTED_WORDS: Set[str] = set()

# Characters that frequently appear inside Bamini / Legacy font tokens (e.g., 'tzf;fk;', 'cyfk;')
# and never inside standard English dictionary words.
_LEGACY_PUNCTUATION_MARKERS = set(";`\\[]{}^~@#$%&*+=<>|")

# NLTK's words corpus includes every single letter ('b'..'z') and obscure 2-letter strings
# that collide directly with common Bamini Tamil syllables (e.g., 'f'='க', 'm'='அ', 'c'='உ',
# 'v'='எ', 'th'='வா', 'fh'='கா', 'gh'='பா', 'rh'='சா', 'jh'='தா', 'kh'='மா', 'eh'='நா', 'dh'='னா', 'yh'='லா').
_BAMINI_COLLISION_STOPLIST = {
    "b", "c", "d", "e", "f", "g", "h", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "th", "fh", "gh", "rh", "jh", "kh", "eh", "dh", "yh", "wh", "zh",
    "fp", "gp", "rp", "jp", "kp", "ep", "dp", "yp", "wp", "zp", "tp", "sp", "up", "op",
}


def _get_english_vocab() -> Set[str]:
    """Lazily loads and caches the NLTK English corpus in memory for O(1) lookup."""
    global _ENGLISH_VOCAB
    if _ENGLISH_VOCAB is not None:
        return _ENGLISH_VOCAB

    try:
        import nltk
        from nltk.corpus import words
        from nltk.data import find

        try:
            find("corpora/words.zip")
        except LookupError:
            logger.info("Downloading NLTK 'words' corpus...")
            nltk.download("words", quiet=True)
        raw_words = {w.lower() for w in words.words()}
        _ENGLISH_VOCAB = raw_words - _BAMINI_COLLISION_STOPLIST
        logger.info(f"Loaded English vocabulary corpus with {len(_ENGLISH_VOCAB)} entries.")
    except Exception as e:
        logger.warning(f"Failed to load NLTK words corpus ({e}); using fallback basic vocabulary.")
        _ENGLISH_VOCAB = {
            "a", "i", "hello", "world", "good", "morning", "evening", "night",
            "welcome", "thank", "you", "please", "yes", "no", "the", "and", "for",
            "with", "from", "this", "that", "university", "computer", "science",
            "engineering", "project", "tamil", "english", "language", "system",
        }
    return _ENGLISH_VOCAB


def set_global_protected_words(words_iterable: Iterable[str]) -> None:
    """Updates the in-memory global protected words set (called by server when DB changes)."""
    global _GLOBAL_PROTECTED_WORDS
    _GLOBAL_PROTECTED_WORDS = {w.strip().lower() for w in words_iterable if w and w.strip()}


def get_global_protected_words() -> Set[str]:
    """Returns a copy of the current global protected words."""
    return set(_GLOBAL_PROTECTED_WORDS)


def _clean_token_for_lookup(word: str) -> str:
    """Strips only outer standard sentence punctuation (.,!?'\"()) while preserving internal characters."""
    return word.strip(".,!?'\"()")


def is_protected_word(word: str, custom_protected_words: Optional[Iterable[str]] = None) -> bool:
    """
    Checks if a word is in the user-provided or admin-configured Protected Words list
    (words that must NOT be transliterated or translated).
    """
    cleaned = _clean_token_for_lookup(word).lower()
    if not cleaned:
        return False
    if cleaned in _GLOBAL_PROTECTED_WORDS:
        return True
    if custom_protected_words:
        custom_set = {w.strip().lower() for w in custom_protected_words if w and w.strip()}
        if cleaned in custom_set:
            return True
    return False


def is_english_word(word: str, custom_protected_words: Optional[Iterable[str]] = None) -> bool:
    """
    Checks if a given word exists in the English vocabulary corpus or user protected words list.

    Args:
        word (str): The word to check.
        custom_protected_words (Optional[Iterable[str]]): Additional protected words from UI.

    Returns:
        bool: True if the word is an English or protected word, False otherwise.
    """
    if not word:
        return False

    # 1. Check user/admin protected corpus first
    if is_protected_word(word, custom_protected_words):
        return True

    # 2. If the token contains legacy font punctuation markers (like ';' in 'tzf;fk;'),
    # it is never a standard English word.
    if any(ch in _LEGACY_PUNCTUATION_MARKERS for ch in word):
        return False

    cleaned = _clean_token_for_lookup(word)
    if not cleaned or not cleaned.isalpha():
        return False

    # 3. Check if token has mixed internal casing typical of Legacy fonts (e.g. 'Nfh', 'nkh', 'jkpo')
    # Standard English words are either all lowercase, all uppercase (acronyms), or Title Case.
    if not (cleaned.islower() or cleaned.isupper() or cleaned.istitle()):
        return False

    vocab = _get_english_vocab()
    return cleaned.lower() in vocab
