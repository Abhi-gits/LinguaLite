"""Shared application constants.

Add a language here (and in the frontend constants) to extend LinguaLite
beyond the initial English ↔ Hindi pair.
"""

MAX_TEXT_LENGTH = 4000

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
}

SUPPORTED_TRANSLATION_PAIRS = {
    ("en", "hi"),
    ("hi", "en"),
}

SUPPORTED_MODES = ("simple", "advanced")
