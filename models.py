import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from word_analysis import ExampleSentence


@dataclass
class WordInput:
    """User input for a single word with optional metadata."""

    word: str
    personal_context: str | None = None
    extra_image_prompt: str | None = None


@dataclass
class ClozeCardInput:
    """User input for a Cloze card with optional metadata."""

    word: str
    personal_context: str | None = None
    extra_image_prompt: str | None = None
    definitions: str | None = None
    card_type: str = "cloze"


@dataclass
class WordCard:
    """Complete flashcard data for a single word."""

    word: str
    ipa: str
    part_of_speech: str
    gender: str | None = None
    verb_type: str | None = None
    personal_context: str | None = None
    extra_image_prompt: str | None = None
    image_path: Path | str | None = None
    audio_path: Path | str | None = None
    is_complete: bool = False
    guid: str = field(default_factory=lambda: str(uuid.uuid4()))
    card_type: str = "vocabulary"

    def mark_complete(self) -> None:
        """Mark this card as complete when user approves all media."""
        self.is_complete = True

    @property
    def short_id(self) -> str:
        """First 8 characters of GUID for media filenames."""
        return self.guid[:8]

    @property
    def needs_image(self) -> bool:
        """Check if image generation is needed."""
        return self.image_path is None

    @property
    def needs_audio(self) -> bool:
        """Check if audio generation is needed."""
        return self.audio_path is None


@dataclass
class ClozeCard:
    """Complete flashcard data for a Cloze card."""

    word: str
    word_analysis: dict
    selected_sentence: str | None = None
    selected_word_form: str | None = None
    personal_context: str | None = None
    extra_prompt: str | None = None
    memory_aid: str | None = None
    image_path: Path | str | None = None
    audio_path: Path | str | None = None
    is_complete: bool = False
    guid: str = field(default_factory=lambda: str(uuid.uuid4()))
    card_type: str = "cloze"

    def mark_complete(self) -> None:
        """Mark this card as complete when user approves all media."""
        self.is_complete = True

    @property
    def short_id(self) -> str:
        """First 8 characters of GUID for media filenames."""
        return self.guid[:8]

    @property
    def needs_image(self) -> bool:
        """Check if image generation is needed."""
        return self.image_path is None

    @property
    def needs_audio(self) -> bool:
        """Check if audio generation is needed."""
        return self.audio_path is None

    # Convenience properties for accessing word_analysis fields
    @property
    def ipa(self) -> str:
        return self.word_analysis.get("ipa", "")

    @property
    def part_of_speech(self) -> str:
        return self.word_analysis.get("part_of_speech", "")

    @property
    def gender(self) -> str | None:
        return self.word_analysis.get("gender")

    @property
    def verb_type(self) -> str | None:
        return self.word_analysis.get("verb_type")

    @property
    def example_sentences(self) -> list[ExampleSentence]:
        return self.word_analysis.get("example_sentences", [])

    # For backward compatibility
    @property
    def definitions(self) -> str | None:
        return self.memory_aid

    @property
    def extra_image_prompt(self) -> str | None:
        return self.extra_prompt

    def create_duplicate_with_sentence(
        self, sentence: str, word_form: str
    ) -> "ClozeCard":
        """Create a new ClozeCard with the same base data but different sentence."""
        return ClozeCard(
            word=self.word,
            word_analysis=self.word_analysis.copy(),
            selected_sentence=sentence,
            selected_word_form=word_form,
            personal_context=self.personal_context,
            extra_prompt=self.extra_prompt,
            memory_aid=self.memory_aid,
            # New card gets new GUID and no media paths
            guid=str(uuid.uuid4()),
            image_path=None,
            audio_path=None,
            is_complete=False,
            card_type=self.card_type,
        )


@dataclass
class Session:
    """Manages a batch of flashcards being created."""

    vocabulary_cards: list[WordCard] = field(default_factory=list)
    cloze_cards: list[ClozeCard] = field(default_factory=list)
    output_directory: Path = field(default_factory=lambda: Path("./output"))
    anki_media_path: Path | None = None

    @property
    def cards(self) -> list[Union[WordCard, ClozeCard]]:
        """Get all cards (vocabulary and cloze combined)."""
        return self.vocabulary_cards + self.cloze_cards

    def add_card(self, card: Union[WordCard, ClozeCard]) -> None:
        """Add a card to the session."""
        if isinstance(card, WordCard):
            self.vocabulary_cards.append(card)
        elif isinstance(card, ClozeCard):
            self.cloze_cards.append(card)

    @property
    def incomplete_cards(self) -> list[Union[WordCard, ClozeCard]]:
        """Get all cards that haven't been marked complete."""
        return [card for card in self.cards if not card.is_complete]

    @property
    def is_complete(self) -> bool:
        """Check if all cards are complete."""
        return all(card.is_complete for card in self.cards)

    def get_media_path(
        self, card: Union["WordCard", "ClozeCard"], extension: str
    ) -> Path:
        """Generate a unique media file path using the card's UUID."""
        clean_word = card.word.lower().replace(" ", "_")
        filename = f"{clean_word}-{card.short_id}{extension}"
        return self.output_directory / filename
