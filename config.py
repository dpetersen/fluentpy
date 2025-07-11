import os
from pathlib import Path

from loguru import logger


def find_anki_collection_media() -> Path | None:
    """Attempt to find Anki's collection.media folder automatically."""
    # Common Anki data paths by platform
    possible_paths = []

    if os.name == "nt":  # Windows
        appdata = os.environ.get("APPDATA")
        if appdata:
            possible_paths.append(
                Path(appdata) / "Anki2" / "User 1" / "collection.media"
            )
    else:  # macOS and Linux
        home = Path.home()
        possible_paths.extend(
            [
                home
                / ".local"
                / "share"
                / "Anki2"
                / "User 1"
                / "collection.media",  # Linux
                home
                / "Library"
                / "Application Support"
                / "Anki2"
                / "User 1"
                / "collection.media",  # macOS
                home
                / "Documents"
                / "Anki2"
                / "User 1"
                / "collection.media",  # Alternative
            ]
        )

    for path in possible_paths:
        if path.exists() and path.is_dir():
            logger.info("Found Anki collection.media folder", path=path)
            return path

    logger.warning("Could not automatically find Anki collection.media folder")
    return None


class AnkiConfig:
    """Configuration for Anki export settings for vocabulary cards."""

    # Note type configuration
    NOTE_TYPE = "2. Picture Words"
    DECK_NAME = "Fluent Forever Spanish::2. Everything Else"

    # Field configuration
    FIELD_NAMES = [
        "Word",
        "Picture",
        "Gender, Personal Connection, Extra Info (Back side)",
        "Pronunciation (Recording and/or IPA)",
        "Test Spelling? (y = yes, blank = no)",
        "guid",
    ]

    # Spanish grammar terms
    SPANISH_PARTS_OF_SPEECH = {
        "noun": "Sustantivo",
        "verb": "Verbo",
        "adjective": "Adjetivo",
        "adverb": "Adverbio",
        "pronoun": "Pronombre",
        "preposition": "Preposición",
        "conjunction": "Conjunción",
        "article": "Artículo",
        "interjection": "Interjección",
    }

    SPANISH_GENDER = {"masculine": "masculino", "feminine": "femenino"}

    SPANISH_VERB_TYPES = {
        "transitive": "transitivo",
        "intransitive": "intransitivo",
        "reflexive": "reflexivo",
        "pronominal": "pronominal",
    }

    def __init__(
        self,
        deck_name: str | None = None,
        anki_media_path: Path | None = None,
        test_spelling: bool = False,
    ):
        self.deck_name = deck_name or self.DECK_NAME
        self.anki_media_path = anki_media_path or find_anki_collection_media()
        self.test_spelling = test_spelling

    def get_spanish_part_of_speech(self, part_of_speech: str) -> str:
        """Get Spanish term for part of speech."""
        return self.SPANISH_PARTS_OF_SPEECH.get(part_of_speech, part_of_speech.title())

    def get_spanish_gender(self, gender: str | None) -> str:
        """Get Spanish term for gender."""
        if not gender:
            return ""
        return self.SPANISH_GENDER.get(gender, gender)

    def get_spanish_verb_type(self, verb_type: str | None) -> str:
        """Get Spanish term for verb type."""
        if not verb_type:
            return ""
        return self.SPANISH_VERB_TYPES.get(verb_type, verb_type)


class ClozeAnkiConfig:
    """Configuration for Anki export settings for Cloze cards."""

    # Note type configuration
    NOTE_TYPE = "3. All-Purpose Card"
    DECK_NAME = "Fluent Forever Spanish::2. Everything Else"

    # Field configuration - exact field names including "- " prefixes
    FIELD_NAMES = [
        "Front (Example with word blanked out or missing)",
        "Front (Picture)",
        "Front (Definitions, base word, etc.)",
        "Back (a single word/phrase, no context)",
        "- The full sentence (no words blanked out)",
        "- Extra Info (Pronunciation, personal connections, conjugations, etc)",
    ]

    # Spanish grammar terms (same as AnkiConfig)
    SPANISH_PARTS_OF_SPEECH = {
        "noun": "Sustantivo",
        "verb": "Verbo",
        "adjective": "Adjetivo",
        "adverb": "Adverbio",
        "pronoun": "Pronombre",
        "preposition": "Preposición",
        "conjunction": "Conjunción",
        "article": "Artículo",
        "interjection": "Interjección",
    }

    SPANISH_GENDER = {"masculine": "masculino", "feminine": "femenino"}

    SPANISH_VERB_TYPES = {
        "transitive": "transitivo",
        "intransitive": "intransitivo",
        "reflexive": "reflexivo",
        "pronominal": "pronominal",
    }

    def __init__(
        self,
        deck_name: str | None = None,
        anki_media_path: Path | None = None,
        guid_column: int = 6,
    ):
        self.deck_name = deck_name or self.DECK_NAME
        self.anki_media_path = anki_media_path or find_anki_collection_media()
        self.guid_column = (
            guid_column  # Cloze cards don't use GUID for duplicate prevention
        )

    def get_spanish_part_of_speech(self, part_of_speech: str) -> str:
        """Get Spanish term for part of speech."""
        return self.SPANISH_PARTS_OF_SPEECH.get(part_of_speech, part_of_speech.title())

    def get_spanish_gender(self, gender: str | None) -> str:
        """Get Spanish term for gender."""
        if not gender:
            return ""
        return self.SPANISH_GENDER.get(gender, gender)

    def get_spanish_verb_type(self, verb_type: str | None) -> str:
        """Get Spanish term for verb type."""
        if not verb_type:
            return ""
        return self.SPANISH_VERB_TYPES.get(verb_type, verb_type)
