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

# NLTK's words corpus includes every single letter ('b'..'z'), obscure 2-letter strings
# that collide with Bamini Tamil syllables, and a few obscure loanwords that collide
# with common Romanized Tamil (Tanglish) words.
_BAMINI_AND_TANGLISH_STOPLIST = {
    # Single letters (except 'a' and 'i') & Bamini 2-letter syllables
    "b", "c", "d", "e", "f", "g", "h", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "th", "fh", "gh", "rh", "jh", "kh", "eh", "dh", "yh", "wh", "zh",
    "fp", "gp", "rp", "jp", "kp", "ep", "dp", "yp", "wp", "zp", "tp", "sp", "up", "op",
    # Common Romanized Tamil (Tanglish) words that collide with obscure NLTK dictionary entries
    "amma", "appa", "anna", "akka", "ponga", "vaanga", "enna", "unna", "enga",
    "anga", "inga", "inge", "idhu", "adhu", "edhu", "sari", "seri", "illa",
    "ille", "illai", "irukku", "iruku", "romba", "konjam", "ippo", "appo", "eppo",
    "kaalai", "maalai", "vanakkam", "nanri", "nandri", "ulagam", "veedu", "ooru", "naadu",
}

# Common modern English words, contractions, and everyday inflected forms not in 1934 Webster's (NLTK words)
_SUPPLEMENTAL_ENGLISH_WORDS = {
    "app", "apps", "online", "offline", "website", "websites", "internet", "email", "emails",
    "software", "hardware", "database", "databases", "server", "servers", "frontend", "backend",
    "dataset", "datasets", "smartphone", "laptop", "computer", "computers", "ok", "okay",
    "hello", "hi", "hey", "bye", "thanks", "thank", "please", "welcome",
    "im", "ive", "id", "ill", "youre", "youve", "youd", "youll", "hes", "shes", "its",
    "were", "weve", "wed", "well", "theyre", "theyve", "theyd", "theyll",
    "dont", "doesnt", "didnt", "cant", "cannot", "wont", "wouldnt", "couldnt", "shouldnt",
    "isnt", "arent", "wasnt", "werent", "hasnt", "havent", "hadnt", "lets", "thats", "whats",
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
        _ENGLISH_VOCAB = (raw_words | _SUPPLEMENTAL_ENGLISH_WORDS) - _BAMINI_AND_TANGLISH_STOPLIST
        logger.info(f"Loaded English vocabulary corpus with {len(_ENGLISH_VOCAB)} entries.")
    except Exception as e:
        logger.warning(f"Failed to load NLTK words corpus ({e}); using fallback basic vocabulary.")
        _ENGLISH_VOCAB = {
            "a", "i", "hello", "world", "good", "morning", "evening", "night",
            "welcome", "thank", "you", "please", "yes", "no", "the", "and", "for",
            "with", "from", "this", "that", "university", "computer", "science",
            "engineering", "project", "tamil", "english", "language", "system",
        } | _SUPPLEMENTAL_ENGLISH_WORDS
    return _ENGLISH_VOCAB


def set_global_protected_words(words_iterable: Iterable[str]) -> None:
    """Updates the in-memory global protected words set (called by server when DB changes)."""
    global _GLOBAL_PROTECTED_WORDS
    _GLOBAL_PROTECTED_WORDS = {w.strip().lower() for w in words_iterable if w and w.strip()}


def get_global_protected_words() -> Set[str]:
    """Returns a copy of the current global protected words."""
    return set(_GLOBAL_PROTECTED_WORDS)


def _clean_token_for_lookup(word: str) -> str:
    """Strips only outer standard sentence punctuation while preserving internal characters."""
    return word.strip(".,!?'\"():-")


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


def _is_inflected_english_in_vocab(w: str, vocab: Set[str]) -> bool:
    """
    Checks if a lowercase word `w` (not directly in NLTK's base lemma list) is a regular
    English inflection (plural -s/-es/-ies/-ves, verb -ed/-ied/-ing, comparative -er/-est,
    adverb -ly) of a known English root word of length >= 3.
    """
    n = len(w)
    if n < 4 or w in _BAMINI_AND_TANGLISH_STOPLIST:
        return False

    candidates = []

    # Plurals & 3rd-person singular verbs (-s, -es, -ies, -ves)
    if w.endswith("ies") and n >= 5:
        candidates.append(w[:-3] + "y")
    if w.endswith("ves") and n >= 5:
        candidates.append(w[:-3] + "f")
        candidates.append(w[:-3] + "fe")
    if w.endswith("es") and n >= 4:
        candidates.append(w[:-2])
        candidates.append(w[:-1])
    if w.endswith("s") and not w.endswith("ss") and n >= 4:
        candidates.append(w[:-1])

    # Past tense & past participles (-ed, -ied, doubled consonant + ed)
    if w.endswith("ied") and n >= 5:
        candidates.append(w[:-3] + "y")
    if w.endswith("ed") and n >= 4:
        candidates.append(w[:-2])
        candidates.append(w[:-1])
        if n >= 5 and w[-3] == w[-4]:
            candidates.append(w[:-3])

    # Present participles / gerunds (-ing, -e + ing, doubled consonant + ing)
    if w.endswith("ing") and n >= 5:
        candidates.append(w[:-3])
        candidates.append(w[:-3] + "e")
        if n >= 6 and w[-4] == w[-5]:
            candidates.append(w[:-4])

    # Comparatives, superlatives & adverbs (-er, -est, -ly)
    if w.endswith("er") and n >= 5:
        candidates.append(w[:-2])
        candidates.append(w[:-1])
        if n >= 6 and w[-3] == w[-4]:
            candidates.append(w[:-3])
    if w.endswith("est") and n >= 5:
        candidates.append(w[:-3])
        candidates.append(w[:-2])
    if w.endswith("ly") and n >= 5:
        candidates.append(w[:-2])
        if w.endswith("ily") and n >= 6:
            candidates.append(w[:-3] + "y")

    return any(len(stem) >= 3 and stem in vocab for stem in candidates)


def is_english_word(word: str, custom_protected_words: Optional[Iterable[str]] = None) -> bool:
    """
    Checks if a given word exists in the English vocabulary corpus (including regular
    morphological inflections and contractions) or user protected words list.

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
    if not cleaned:
        return False

    # Handle standard English contractions and possessives (e.g., "don't", "I'm", "student's")
    if "'" in cleaned:
        no_apostrophe = cleaned.replace("'", "")
        if not no_apostrophe.isalpha():
            return False
        vocab = _get_english_vocab()
        if no_apostrophe.lower() in vocab:
            return True
        if cleaned.lower().endswith("'s") and len(cleaned) >= 4:
            base = cleaned[:-2]
            return is_english_word(base, custom_protected_words)
        return False

    if not cleaned.isalpha():
        return False

    # 3. Check if token has mixed internal casing typical of Legacy fonts (e.g. 'Nfh', 'nkh', 'jkpo')
    # Standard English words are either all lowercase, all uppercase (acronyms), or Title Case.
    if not (cleaned.islower() or cleaned.isupper() or cleaned.istitle()):
        return False

    lower_w = cleaned.lower()
    if lower_w in _BAMINI_AND_TANGLISH_STOPLIST:
        return False

    vocab = _get_english_vocab()
    if lower_w in vocab:
        return True

    return _is_inflected_english_in_vocab(lower_w, vocab)
