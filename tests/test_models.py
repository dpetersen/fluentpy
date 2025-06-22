import tempfile
from pathlib import Path

from models import Session, WordCard, WordInput


class TestWordInput:
    def test_create_minimal(self):
        """Test creating WordInput with just the required word."""
        word_input = WordInput(word="hola")
        assert word_input.word == "hola"
        assert word_input.personal_context is None
        assert word_input.extra_image_prompt is None

    def test_create_with_metadata(self):
        """Test creating WordInput with all fields."""
        word_input = WordInput(
            word="correr",
            personal_context="I run every morning",
            extra_image_prompt="person running in a park",
        )
        assert word_input.word == "correr"
        assert word_input.personal_context == "I run every morning"
        assert word_input.extra_image_prompt == "person running in a park"


class TestWordCard:
    def test_create_minimal(self):
        """Test creating WordCard with minimal required fields."""
        card = WordCard(
            word="gato",
            ipa="ˈga.to",
            part_of_speech="noun",
        )
        assert card.word == "gato"
        assert card.ipa == "ˈga.to"
        assert card.part_of_speech == "noun"
        assert card.is_complete is False
        assert card.image_path is None
        assert card.audio_path is None

    def test_needs_media(self):
        """Test needs_image and needs_audio properties."""
        card = WordCard(word="perro", ipa="ˈpe.ro", part_of_speech="noun")
        assert card.needs_image is True
        assert card.needs_audio is True

        card.image_path = Path("perro.jpg")
        assert card.needs_image is False
        assert card.needs_audio is True

        card.audio_path = Path("perro.mp3")
        assert card.needs_image is False
        assert card.needs_audio is False

    def test_mark_complete(self):
        """Test marking a card as complete."""
        card = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
        assert card.is_complete is False

        card.mark_complete()
        assert card.is_complete is True


class TestSession:
    def test_create_empty(self):
        """Test creating an empty session."""
        session = Session()
        assert len(session.cards) == 0
        assert session.output_directory == Path("./output")
        assert session.anki_media_path is None
        assert session.is_complete is True

    def test_add_cards(self):
        """Test adding cards to a session."""
        session = Session()
        card1 = WordCard(word="sol", ipa="sol", part_of_speech="noun")
        card2 = WordCard(word="luna", ipa="ˈlu.na", part_of_speech="noun")

        session.add_card(card1)
        session.add_card(card2)

        assert len(session.cards) == 2
        assert session.cards[0].word == "sol"
        assert session.cards[1].word == "luna"

    def test_incomplete_cards(self):
        """Test getting incomplete cards from session."""
        session = Session()
        card1 = WordCard(word="agua", ipa="ˈa.ɣwa", part_of_speech="noun")
        card2 = WordCard(word="fuego", ipa="ˈfwe.ɣo", part_of_speech="noun")
        card3 = WordCard(word="tierra", ipa="ˈtje.ra", part_of_speech="noun")

        session.add_card(card1)
        session.add_card(card2)
        session.add_card(card3)

        card2.mark_complete()

        incomplete = session.incomplete_cards
        assert len(incomplete) == 2
        assert card1 in incomplete
        assert card3 in incomplete
        assert card2 not in incomplete

    def test_is_complete(self):
        """Test session completion status."""
        session = Session()
        assert session.is_complete is True

        card1 = WordCard(word="rojo", ipa="ˈro.xo", part_of_speech="adjective")
        session.add_card(card1)
        assert session.is_complete is False

        card1.mark_complete()
        assert session.is_complete is True

    def test_get_media_path_unique(self):
        """Test generating unique media paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))

            path1 = session.get_media_path("casa", ".jpg")
            assert path1 == Path(tmpdir) / "casa.jpg"

            # Add a card with that path
            card = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
            card.image_path = path1
            session.add_card(card)

            # Next call should generate a different path
            path2 = session.get_media_path("casa", ".jpg")
            assert path2 == Path(tmpdir) / "casa_2.jpg"

    def test_get_media_path_special_characters(self):
        """Test media path generation with special characters."""
        session = Session()
        path = session.get_media_path("niño pequeño", ".mp3")
        assert "niño_pequeño.mp3" in str(path)