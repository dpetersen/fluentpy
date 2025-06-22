import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WordInput:
    """User input for a single word with optional metadata."""

    word: str
    personal_context: str | None = None
    extra_image_prompt: str | None = None


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
    image_path: Path | None = None
    audio_path: Path | None = None
    is_complete: bool = False
    guid: str = field(default_factory=lambda: str(uuid.uuid4()))

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
class Session:
    """Manages a batch of flashcards being created."""

    cards: list[WordCard] = field(default_factory=list)
    output_directory: Path = field(default_factory=lambda: Path("./output"))
    anki_media_path: Path | None = None

    def add_card(self, card: WordCard) -> None:
        """Add a card to the session."""
        self.cards.append(card)

    @property
    def incomplete_cards(self) -> list[WordCard]:
        """Get all cards that haven't been marked complete."""
        return [card for card in self.cards if not card.is_complete]

    @property
    def is_complete(self) -> bool:
        """Check if all cards are complete."""
        return all(card.is_complete for card in self.cards)

    def get_media_path(self, card: "WordCard", extension: str) -> Path:
        """Generate a unique media file path using the card's UUID."""
        clean_word = card.word.lower().replace(" ", "_")
        filename = f"{clean_word}-{card.short_id}{extension}"
        return self.output_directory / filename