"""Shared language registry and request limits."""

MAX_TEXT_LENGTH = 4000

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
}

EXPERIMENTAL_LANGUAGES = frozenset({"ta", "te", "kn", "ml", "bn", "mr", "gu", "pa"})

SUPPORTED_TRANSLATION_PAIRS = {
    (source, target)
    for source in SUPPORTED_LANGUAGES
    for target in SUPPORTED_LANGUAGES
    if source != target
}

SUPPORTED_MODES = ("simple", "advanced")
