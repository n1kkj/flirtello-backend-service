import gettext
from pathlib import Path
from typing import Callable, Optional


def get_gettext_for_language(language_code: Optional[str]) -> Callable[[str], str]:
    """Return gettext function for the given language.

    Falls back to base language (e.g., ru for ru-RU) and then to en.
    """
    locales_dir = Path(__file__).resolve().parent.parent / "locales"

    languages: list[str] = []
    if language_code:
        lc = str(language_code)
        languages.append(lc)
        # Try base part without region
        base = lc.replace("_", "-").split("-")[0]
        if base and base != lc:
            languages.append(base)
    languages.append("en")

    translation = gettext.translation(
        domain="messages", localedir=str(locales_dir), languages=languages, fallback=True
    )
    return translation.gettext


