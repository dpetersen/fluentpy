import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from models import ClozeCard, ClozeCardInput, Session, WordCard, WordInput
from session import (
    create_session,
    generate_media_for_session,
    regenerate_audio,
    regenerate_image,
)


class TestCreateSession:
    @pytest.mark.asyncio
    @patch("session.analyze_word")
    @patch("session.AsyncOpenAI")
    async def test_creates_session_with_analyzed_words(self, mock_openai, mock_analyze):
        """Test that create_session analyzes words and creates WordCards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Mock word analysis
            mock_analyze.side_effect = [
                {
                    "ipa": "ˈo.la",
                    "part_of_speech": "interjection",
                    "gender": None,
                    "verb_type": None,
                },
                {
                    "ipa": "ˈga.to",
                    "part_of_speech": "noun",
                    "gender": "masculine",
                    "verb_type": None,
                },
            ]

            word_inputs = [
                WordInput(word="hola", personal_context="greeting"),
                WordInput(word="gato", extra_image_prompt="orange cat"),
            ]

            session = await create_session(vocabulary_inputs=word_inputs, cloze_inputs=[], output_directory=output_dir)

            # Verify session structure
            assert len(session.cards) == 2
            assert session.output_directory == output_dir

            # Verify first card
            card1 = session.cards[0]
            assert card1.word == "hola"
            assert card1.ipa == "ˈo.la"
            assert card1.part_of_speech == "interjection"
            assert card1.personal_context == "greeting"

            # Verify second card
            card2 = session.cards[1]
            assert card2.word == "gato"
            assert card2.ipa == "ˈga.to"
            assert card2.part_of_speech == "noun"
            assert card2.gender == "masculine"
            assert card2.extra_image_prompt == "orange cat"

    @pytest.mark.asyncio
    @patch("session.analyze_word")
    @patch("session.AsyncOpenAI")
    async def test_creates_default_output_directory(self, mock_openai, mock_analyze):
        """Test that create_session creates default output directory."""
        mock_analyze.return_value = {
            "ipa": "ˈo.la",
            "part_of_speech": "interjection",
            "gender": None,
            "verb_type": None,
        }

        word_inputs = [WordInput(word="hola")]
        session = await create_session(vocabulary_inputs=word_inputs)

        assert session.output_directory == Path("./output")
        # Note: Directory creation is tested by ensuring no exception is raised


class TestGenerateMediaForSession:
    @pytest.mark.asyncio
    @patch("session.generate_audio")
    @patch("session.generate_image")
    @patch("session.AsyncElevenLabs")
    @patch("session.AsyncOpenAI")
    async def test_generates_media_for_all_cards(
        self, mock_openai, mock_elevenlabs, mock_gen_image, mock_gen_audio
    ):
        """Test that media is generated for all cards in session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))

            # Add test cards
            card1 = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
            card2 = WordCard(word="perro", ipa="ˈpe.ro", part_of_speech="noun")
            session.add_card(card1)
            session.add_card(card2)

            # Mock successful generation
            mock_gen_image.return_value = "path/to/image.jpg"
            mock_gen_audio.return_value = "path/to/audio.mp3"

            await generate_media_for_session(session)

            # Verify media generation was called for both cards
            assert mock_gen_image.call_count == 2
            assert mock_gen_audio.call_count == 2

            # Verify paths were set on cards
            assert card1.image_path is not None
            assert card1.audio_path is not None
            assert card2.image_path is not None
            assert card2.audio_path is not None

    @pytest.mark.asyncio
    @patch("session.generate_audio")
    @patch("session.generate_image")
    @patch("session.AsyncElevenLabs")
    @patch("session.AsyncOpenAI")
    async def test_handles_generation_failures(
        self, mock_openai, mock_elevenlabs, mock_gen_image, mock_gen_audio
    ):
        """Test that generation failures are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(word="test", ipa="test", part_of_speech="noun")
            session.add_card(card)

            # Mock generation failures
            mock_gen_image.side_effect = Exception("Image generation failed")
            mock_gen_audio.side_effect = Exception("Audio generation failed")

            # Should not raise exception
            await generate_media_for_session(session)

            # Paths should remain None
            assert card.image_path is None
            assert card.audio_path is None


class TestRegenerateImage:
    @pytest.mark.asyncio
    @patch("session.generate_image")
    @patch("session.AsyncOpenAI")
    async def test_regenerates_image_successfully(self, mock_openai, mock_gen_image):
        """Test successful image regeneration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")

            # Mock successful regeneration
            expected_path = session.get_media_path(card, ".jpg")
            mock_gen_image.return_value = str(expected_path)

            result = await regenerate_image(session, card, "additional context")

            assert result is True
            assert card.image_path == expected_path

    @pytest.mark.asyncio
    @patch("session.generate_image")
    @patch("session.AsyncOpenAI")
    async def test_regenerate_image_handles_failure(self, mock_openai, mock_gen_image):
        """Test that image regeneration handles failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(word="test", ipa="test", part_of_speech="noun")

            # Mock generation failure
            mock_gen_image.side_effect = Exception("Generation failed")

            result = await regenerate_image(session, card)

            assert result is False
            assert card.image_path is None


class TestRegenerateAudio:
    @pytest.mark.asyncio
    @patch("session.generate_audio")
    @patch("session.AsyncElevenLabs")
    async def test_regenerates_audio_successfully(
        self, mock_elevenlabs, mock_gen_audio
    ):
        """Test successful audio regeneration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(word="hola", ipa="ˈo.la", part_of_speech="interjection")

            # Mock successful regeneration
            expected_path = session.get_media_path(card, ".mp3")
            mock_gen_audio.return_value = str(expected_path)

            result = await regenerate_audio(session, card)

            assert result is True
            assert card.audio_path == expected_path

    @pytest.mark.asyncio
    @patch("session.generate_audio")
    @patch("session.AsyncElevenLabs")
    async def test_regenerate_audio_handles_failure(
        self, mock_elevenlabs, mock_gen_audio
    ):
        """Test that audio regeneration handles failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(word="test", ipa="test", part_of_speech="noun")

            # Mock generation failure
            mock_gen_audio.side_effect = Exception("Generation failed")

            result = await regenerate_audio(session, card)

            assert result is False
            assert card.audio_path is None


class TestCreateSessionWithClozeCards:
    @pytest.mark.asyncio
    @patch("session.analyze_word")
    @patch("session.AsyncOpenAI")
    async def test_creates_session_with_cloze_cards(self, mock_openai, mock_analyze):
        """Test that create_session handles ClozeCardInput objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Mock word analysis with example sentences
            mock_analyze.return_value = {
                "ipa": "ˈka.sa",
                "part_of_speech": "sustantivo",
                "gender": "femenino",
                "example_sentences": [
                    "La casa es grande.",
                    "Vivo en una casa.",
                    "Mi casa tiene jardín.",
                ]
            }
            
            cloze_inputs = [
                ClozeCardInput(word="casa", personal_context="my home")
            ]
            
            session = await create_session(
                vocabulary_inputs=[],
                cloze_inputs=cloze_inputs,
                output_directory=output_dir
            )
            
            # Verify session structure
            assert len(session.vocabulary_cards) == 0
            assert len(session.cloze_cards) == 1
            assert session.output_directory == output_dir
            
            # Verify cloze card
            cloze_card = session.cloze_cards[0]
            assert cloze_card.word == "casa"
            assert cloze_card.word_analysis["ipa"] == "ˈka.sa"
            assert cloze_card.word_analysis["part_of_speech"] == "sustantivo"
            assert cloze_card.selected_sentence is None  # Not selected yet
            assert cloze_card.personal_context == "my home"
            
    @pytest.mark.asyncio
    @patch("session.analyze_word")
    @patch("session.AsyncOpenAI")
    async def test_creates_session_with_mixed_card_types(self, mock_openai, mock_analyze):
        """Test create_session with both vocabulary and cloze inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Mock different analyses for different words
            mock_analyze.side_effect = [
                # Vocabulary word analysis
                {
                    "ipa": "ˈo.la",
                    "part_of_speech": "interjección",
                    "gender": None,
                    "example_sentences": ["Hola amigo."]
                },
                # Cloze word analysis
                {
                    "ipa": "ˈpe.ro",
                    "part_of_speech": "sustantivo",
                    "gender": "masculino",
                    "example_sentences": [
                        "El perro ladra.",
                        "Mi perro es pequeño.",
                        "Ese perro es amigable."
                    ]
                }
            ]
            
            vocabulary_inputs = [WordInput(word="hola")]
            cloze_inputs = [ClozeCardInput(word="perro")]
            
            session = await create_session(
                vocabulary_inputs=vocabulary_inputs,
                cloze_inputs=cloze_inputs,
                output_directory=output_dir
            )
            
            # Verify both card types were created
            assert len(session.vocabulary_cards) == 1
            assert len(session.cloze_cards) == 1
            
            # Verify vocabulary card
            vocab_card = session.vocabulary_cards[0]
            assert vocab_card.word == "hola"
            assert vocab_card.ipa == "ˈo.la"
            
            # Verify cloze card
            cloze_card = session.cloze_cards[0]
            assert cloze_card.word == "perro"
            assert cloze_card.word_analysis["ipa"] == "ˈpe.ro"
            assert len(cloze_card.word_analysis["example_sentences"]) == 3


class TestGenerateMediaForClozeCards:
    @pytest.mark.asyncio
    @patch("session.generate_audio")
    @patch("session.generate_image")
    @patch("session.AsyncElevenLabs")
    @patch("session.AsyncOpenAI")
    async def test_generates_media_for_cloze_cards(self, mock_openai, mock_elevenlabs, mock_gen_image, mock_gen_audio):
        """Test media generation for ClozeCard objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            
            # Create a cloze card with selected sentence
            word_analysis = {
                "ipa": "ˈka.sa",
                "part_of_speech": "sustantivo",
                "gender": "femenino",
                "example_sentences": ["La casa es grande."]
            }
            cloze_card = ClozeCard(
                word="casa",
                word_analysis=word_analysis,
                selected_sentence="La casa es grande."
            )
            session.cloze_cards = [cloze_card]
            
            # Mock successful generation
            mock_gen_image.return_value = "path/to/image.jpg"
            mock_gen_audio.return_value = "path/to/audio.mp3"
            
            await generate_media_for_session(session)
            
            # Verify media generation was called
            assert mock_gen_image.call_count == 1
            assert mock_gen_audio.call_count == 1
            
            # Verify paths were set on cloze card
            assert cloze_card.image_path is not None
            assert cloze_card.audio_path is not None
