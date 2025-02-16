import re

def contains_url(input_text: str) -> bool:
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return re.search(url_pattern, input_text) is not None

def contains_phone_number(input_text: str) -> bool:
    phone_pattern = re.compile(
        r'(\+?\d{1,4}[\s-])?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}'
    )
    return re.search(phone_pattern, input_text) is not None

def starts_and_ends_with_brackets(input_text: str) -> bool:
    return input_text.startswith('[') and input_text.endswith(']')

def is_special_case(input_text: str) -> bool:
    return contains_url(input_text) or contains_phone_number(input_text) or starts_and_ends_with_brackets(input_text)
    