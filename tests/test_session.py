import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from models import Session, WordCard, WordInput
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
                {"ipa": "ˈo.la", "part_of_speech": "interjection", "gender": None, "verb_type": None},
                {"ipa": "ˈga.to", "part_of_speech": "noun", "gender": "masculine", "verb_type": None},
            ]
            
            word_inputs = [
                WordInput(word="hola", personal_context="greeting"),
                WordInput(word="gato", extra_image_prompt="orange cat"),
            ]
            
            session = await create_session(word_inputs, output_dir)
            
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
            "ipa": "ˈo.la", "part_of_speech": "interjection", "gender": None, "verb_type": None
        }
        
        word_inputs = [WordInput(word="hola")]
        session = await create_session(word_inputs)
        
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
            card = WordCard(
                word="casa", ipa="ˈka.sa", part_of_speech="noun"
            )
            
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
    async def test_regenerates_audio_successfully(self, mock_elevenlabs, mock_gen_audio):
        """Test successful audio regeneration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(
                word="hola", ipa="ˈo.la", part_of_speech="interjection"
            )
            
            # Mock successful regeneration
            expected_path = session.get_media_path(card, ".mp3")
            mock_gen_audio.return_value = str(expected_path)
            
            result = await regenerate_audio(session, card)
            
            assert result is True
            assert card.audio_path == expected_path

    @pytest.mark.asyncio
    @patch("session.generate_audio")
    @patch("session.AsyncElevenLabs")
    async def test_regenerate_audio_handles_failure(self, mock_elevenlabs, mock_gen_audio):
        """Test that audio regeneration handles failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            card = WordCard(word="test", ipa="test", part_of_speech="noun")
            
            # Mock generation failure
            mock_gen_audio.side_effect = Exception("Generation failed")
            
            result = await regenerate_audio(session, card)
            
            assert result is False
            assert card.audio_path is None