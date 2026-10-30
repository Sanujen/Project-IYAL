import re

_URL_PATTERN = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)
_PHONE_PATTERN = re.compile(
    r"(\+?\d{1,4}[\s-])?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}"
)
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def contains_url(input_text: str) -> bool:
    return _URL_PATTERN.search(input_text) is not None


def contains_phone_number(input_text: str) -> bool:
    return _PHONE_PATTERN.search(input_text) is not None


def starts_and_ends_with_brackets(input_text: str) -> bool:
    return len(input_text) >= 2 and input_text.startswith("[") and input_text.endswith("]")


def contains_email(input_text: str) -> bool:
    return _EMAIL_PATTERN.search(input_text) is not None


def is_special_case(input_text: str) -> bool:
    """
    Checks if a token is a URL, phone number, bracketed tag, or email address
    that should remain untouched during normalization.
    """
    return (
        contains_url(input_text)
        or contains_phone_number(input_text)
        or starts_and_ends_with_brackets(input_text)
        or contains_email(input_text)
    )
