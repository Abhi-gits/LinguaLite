from app.constants import SUPPORTED_LANGUAGES


def build_translation_prompt(
    *,
    text: str,
    source_language: str,
    target_language: str,
    mode: str | None = None,
    style: str | None = None,
) -> str:
    source_name = SUPPORTED_LANGUAGES[source_language]
    target_name = SUPPORTED_LANGUAGES[target_language]

    selected_style = style or ("natural" if mode == "simple" else "formal")
    if style is None and mode == "advanced":
        guidance = (
            "Use Advanced mode. Preserve meaning, names, numbers, punctuation, tone, "
            "and important technical terms. Prefer context-sensitive wording and keep "
            "terminology consistent."
        )
    elif style is None and mode == "simple":
        guidance = "Use Simple mode and prefer natural, clear language for general readers."
    elif selected_style == "formal":
        guidance = (
            "Use a formal, polished register appropriate for professional or respectful "
            "communication. Preserve meaning, names, numbers, punctuation, and technical terms."
        )
    elif selected_style == "casual":
        guidance = (
            "Use a casual, conversational register while preserving meaning, names, numbers, "
            "punctuation, and technical terms."
        )
    elif selected_style == "literal":
        guidance = (
            "Translate as literally as possible while keeping the result grammatical and "
            "understandable. Preserve meaning, names, numbers, punctuation, and technical terms."
        )
    else:
        guidance = (
            "Use a natural, clear register that sounds fluent to a native speaker. "
            "Preserve meaning, names, numbers, punctuation, and technical terms."
        )

    return (
        f"You are a professional translator.\n"
        f"Translate the text from {source_name} ({source_language}) "
        f"to {target_name} ({target_language}).\n"
        "Return only the translation, with no explanation, labels, or commentary.\n"
        f"{guidance}\n"
        "Do not invent content that is not present in the source.\n\n"
        "Source text:\n"
        f"{text}"
    )


def extract_translation(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()

    return text
