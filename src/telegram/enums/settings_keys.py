from enum import Enum


class UserSettingsKeys(Enum):
    """Enum for user settings keys stored in hstore"""

    CURRENT_CHAR_ID = "angel_char_id"
    CONFIG_ID = "config_id"
    LANGUAGE = "language"
    LANGUAGE_OVERRIDE = "language_override"

    def __str__(self) -> str:
        """Return the value of the enum when converting to string"""
        return self.value
