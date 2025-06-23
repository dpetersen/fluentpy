import tempfile
from pathlib import Path

from models import ClozeCard, ClozeCardInput, Session, WordCard, WordInput


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

    def test_guid_generation(self):
        """Test that each card gets a unique GUID."""
        card1 = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
        card2 = WordCard(word="perro", ipa="ˈpe.ro", part_of_speech="noun")

        # Each card should have a GUID
        assert card1.guid is not None
        assert card2.guid is not None

        # GUIDs should be different
        assert card1.guid != card2.guid

        # GUIDs should be valid UUID format (36 chars with dashes)
        assert len(card1.guid) == 36
        assert card1.guid.count("-") == 4

    def test_short_id(self):
        """Test short_id property returns first 8 characters of GUID."""
        card = WordCard(word="test", ipa="test", part_of_speech="noun")

        assert len(card.short_id) == 8
        assert card.short_id == card.guid[:8]


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

    def test_get_media_path_with_uuid(self):
        """Test media path generation with UUID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")

            path = session.get_media_path(card, ".jpg")

            # Should contain word and short UUID
            assert "casa-" in str(path)
            assert str(path).endswith(".jpg")
            assert len(card.short_id) == 8

    def test_get_media_path_special_characters(self):
        """Test media path generation with special characters."""
        session = Session()
        card = WordCard(
            word="niño pequeño", ipa="ˈni.ɲo pe.ˈke.ɲo", part_of_speech="noun"
        )
        path = session.get_media_path(card, ".mp3")
        assert "niño_pequeño-" in str(path)
        assert str(path).endswith(".mp3")


class TestClozeCardInput:
    def test_create_minimal(self):
        """Test creating ClozeCardInput with just the required word."""
        cloze_input = ClozeCardInput(word="casa")
        assert cloze_input.word == "casa"
        assert cloze_input.personal_context is None
        assert cloze_input.extra_image_prompt is None

    def test_create_with_metadata(self):
        """Test creating ClozeCardInput with all fields."""
        cloze_input = ClozeCardInput(
            word="estudiar",
            personal_context="I study Spanish every day",
            extra_image_prompt="student with books",
        )
        assert cloze_input.word == "estudiar"
        assert cloze_input.personal_context == "I study Spanish every day"
        assert cloze_input.extra_image_prompt == "student with books"


class TestClozeCard:
    def test_create_minimal(self):
        """Test creating ClozeCard with minimal required fields."""
        word_analysis = {
            "ipa": "ˈka.sa",
            "part_of_speech": "sustantivo",
            "gender": "femenino",
            "example_sentences": [
                "La casa es grande.",
                "Vivo en una casa.",
                "Mi casa tiene jardín."
            ]
        }
        
        card = ClozeCard(
            word="casa",
            word_analysis=word_analysis,
            selected_sentence="La casa es grande."
        )
        
        assert card.word == "casa"
        assert card.word_analysis == word_analysis
        assert card.selected_sentence == "La casa es grande."
        assert card.is_complete is False
        assert card.image_path is None
        assert card.audio_path is None
        assert card.guid is not None

    def test_create_with_full_data(self):
        """Test creating ClozeCard with all fields."""
        word_analysis = {
            "ipa": "es.tu.ˈdjaɾ",
            "part_of_speech": "verbo",
            "gender": None,
            "example_sentences": [
                "Voy a estudiar español.",
                "Ella estudia medicina.",
                "Estudiamos juntos."
            ]
        }
        
        card = ClozeCard(
            word="estudiar",
            word_analysis=word_analysis,
            selected_sentence="Voy a estudiar español.",
            image_path="estudiar-abc123.jpg",
            audio_path="estudiar-abc123.mp3",
            memory_aid="Think of student with books",
            extra_prompt="Add university setting"
        )
        
        assert card.word == "estudiar"
        assert card.selected_sentence == "Voy a estudiar español."
        assert card.image_path == "estudiar-abc123.jpg"
        assert card.audio_path == "estudiar-abc123.mp3"
        assert card.memory_aid == "Think of student with books"
        assert card.extra_prompt == "Add university setting"

    def test_needs_media(self):
        """Test needs_image and needs_audio properties."""
        word_analysis = {
            "ipa": "ˈpe.ro",
            "part_of_speech": "sustantivo",
            "gender": "masculino",
            "example_sentences": ["El perro ladra."]
        }
        
        card = ClozeCard(
            word="perro",
            word_analysis=word_analysis,
            selected_sentence="El perro ladra."
        )
        
        assert card.needs_image is True
        assert card.needs_audio is True

        card.image_path = "perro.jpg"
        assert card.needs_image is False
        assert card.needs_audio is True

        card.audio_path = "perro.mp3"
        assert card.needs_image is False
        assert card.needs_audio is False

    def test_mark_complete(self):
        """Test marking a ClozeCard as complete."""
        word_analysis = {
            "ipa": "ˈli.bɾo",
            "part_of_speech": "sustantivo",
            "gender": "masculino",
            "example_sentences": ["Leo un libro."]
        }
        
        card = ClozeCard(
            word="libro",
            word_analysis=word_analysis,
            selected_sentence="Leo un libro."
        )
        
        assert card.is_complete is False
        card.mark_complete()
        assert card.is_complete is True

    def test_guid_generation(self):
        """Test that each ClozeCard gets a unique GUID."""
        word_analysis1 = {
            "ipa": "ˈa.ɣwa",
            "part_of_speech": "sustantivo",
            "gender": "femenino",
            "example_sentences": ["Bebo agua."]
        }
        
        word_analysis2 = {
            "ipa": "ˈfwe.ɣo",
            "part_of_speech": "sustantivo",
            "gender": "masculino",
            "example_sentences": ["El fuego es caliente."]
        }
        
        card1 = ClozeCard(word="agua", word_analysis=word_analysis1, selected_sentence="Bebo agua.")
        card2 = ClozeCard(word="fuego", word_analysis=word_analysis2, selected_sentence="El fuego es caliente.")

        # Each card should have a GUID
        assert card1.guid is not None
        assert card2.guid is not None

        # GUIDs should be different
        assert card1.guid != card2.guid

        # GUIDs should be valid UUID format (36 chars with dashes)
        assert len(card1.guid) == 36
        assert card1.guid.count("-") == 4

    def test_short_id(self):
        """Test short_id property returns first 8 characters of GUID."""
        word_analysis = {
            "ipa": "test",
            "part_of_speech": "sustantivo",
            "gender": "masculino",
            "example_sentences": ["Test sentence."]
        }
        
        card = ClozeCard(word="test", word_analysis=word_analysis, selected_sentence="Test sentence.")

        assert len(card.short_id) == 8
        assert card.short_id == card.guid[:8]
