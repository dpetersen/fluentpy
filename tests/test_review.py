import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from models import Session, WordCard
from review import (
    display_card_media,
    handle_audio_regeneration,
    handle_image_regeneration,
    review_card,
    show_session_summary,
)


class TestDisplayCardMedia:
    @pytest.mark.asyncio
    @patch("review.view_image")
    async def test_displays_image_when_available(self, mock_view_image):
        """Test that image is displayed when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "test.jpg"
            image_path.touch()
            
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", image_path=image_path
            )
            
            await display_card_media(card)
            
            mock_view_image.assert_called_once_with(str(image_path))

    @pytest.mark.asyncio
    @patch("review.view_image")
    async def test_handles_image_display_error(self, mock_view_image):
        """Test that image display errors are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "test.jpg"
            image_path.touch()
            
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", image_path=image_path
            )
            
            mock_view_image.side_effect = Exception("Display failed")
            
            # Should not raise exception
            await display_card_media(card)

    @pytest.mark.asyncio
    async def test_handles_missing_media(self):
        """Test display when no media files exist."""
        card = WordCard(word="test", ipa="test", part_of_speech="noun")
        
        # Should not raise exception
        await display_card_media(card)

    @pytest.mark.asyncio
    async def test_displays_audio_path_when_available(self):
        """Test that audio path is shown when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.touch()
            
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", audio_path=audio_path
            )
            
            # Should not raise exception
            await display_card_media(card)


class TestHandleImageRegeneration:
    @pytest.mark.asyncio
    @patch("review.regenerate_image")
    @patch("review.display_card_media")
    @patch("review.questionary.text")
    async def test_regenerates_image_with_context(
        self, mock_text, mock_display, mock_regen
    ):
        """Test image regeneration with additional context."""
        session = Session()
        card = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
        
        mock_text.return_value.ask.return_value = "make it colorful"
        mock_regen.return_value = True
        
        await handle_image_regeneration(session, card)
        
        mock_regen.assert_called_once_with(session, card, "make it colorful")
        mock_display.assert_called_once_with(card)

    @pytest.mark.asyncio
    @patch("review.regenerate_image")
    @patch("review.questionary.text")
    async def test_regenerates_image_without_context(self, mock_text, mock_regen):
        """Test image regeneration without additional context."""
        session = Session()
        card = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
        
        mock_text.return_value.ask.return_value = ""
        mock_regen.return_value = True
        
        await handle_image_regeneration(session, card)
        
        mock_regen.assert_called_once_with(session, card, None)

    @pytest.mark.asyncio
    @patch("review.regenerate_image")
    @patch("review.questionary.text")
    async def test_handles_regeneration_failure(self, mock_text, mock_regen):
        """Test handling of regeneration failure."""
        session = Session()
        card = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
        
        mock_text.return_value.ask.return_value = ""
        mock_regen.return_value = False
        
        # Should not raise exception
        await handle_image_regeneration(session, card)


class TestHandleAudioRegeneration:
    @pytest.mark.asyncio
    @patch("review.regenerate_audio")
    async def test_regenerates_audio_successfully(self, mock_regen):
        """Test successful audio regeneration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session()
            card = WordCard(word="hola", ipa="ˈo.la", part_of_speech="interjection")
            
            mock_regen.return_value = True
            card.audio_path = Path(tmpdir) / "new_audio.mp3"
            
            await handle_audio_regeneration(session, card)
            
            mock_regen.assert_called_once_with(session, card)

    @pytest.mark.asyncio
    @patch("review.regenerate_audio")
    async def test_handles_regeneration_failure(self, mock_regen):
        """Test handling of audio regeneration failure."""
        session = Session()
        card = WordCard(word="hola", ipa="ˈo.la", part_of_speech="interjection")
        
        mock_regen.return_value = False
        
        # Should not raise exception
        await handle_audio_regeneration(session, card)


class TestReviewCard:
    @pytest.mark.asyncio
    @patch("review.display_card_media")
    @patch("review.questionary.select")
    async def test_approves_card(self, mock_select, mock_display):
        """Test approving a card marks it complete."""
        session = Session()
        card = WordCard(word="test", ipa="test", part_of_speech="noun")
        
        mock_select.return_value.ask.return_value = "✅ Approve this card"
        
        await review_card(session, card)
        
        assert card.is_complete is True

    @pytest.mark.asyncio
    @patch("review.handle_image_regeneration")
    @patch("review.display_card_media")
    @patch("review.questionary.select")
    async def test_regenerates_image(self, mock_select, mock_display, mock_handle_image):
        """Test that image regeneration option calls handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session()
            image_path = Path(tmpdir) / "test.jpg"
            image_path.touch()
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", image_path=image_path
            )
            
            # First call regenerate, then approve
            mock_select.return_value.ask.side_effect = [
                "🖼️  Regenerate image",
                "✅ Approve this card",
            ]
            
            await review_card(session, card)
            
            mock_handle_image.assert_called_once_with(session, card)

    @pytest.mark.asyncio
    @patch("review.handle_audio_regeneration")
    @patch("review.display_card_media")
    @patch("review.questionary.select")
    async def test_regenerates_audio(self, mock_select, mock_display, mock_handle_audio):
        """Test that audio regeneration option calls handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session()
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.touch()
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", audio_path=audio_path
            )
            
            # First call regenerate, then approve
            mock_select.return_value.ask.side_effect = [
                "🔊 Regenerate audio",
                "✅ Approve this card",
            ]
            
            await review_card(session, card)
            
            mock_handle_audio.assert_called_once_with(session, card)


class TestShowSessionSummary:
    def test_displays_complete_session_summary(self):
        """Test that session summary displays all relevant information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session(output_directory=Path(tmpdir))
            
            # Add completed card with media
            card1 = WordCard(word="casa", ipa="ˈka.sa", part_of_speech="noun")
            card1.image_path = Path(tmpdir) / "casa.jpg"
            card1.audio_path = Path(tmpdir) / "casa.mp3"
            card1.mark_complete()
            
            # Add incomplete card
            card2 = WordCard(word="perro", ipa="ˈpe.ro", part_of_speech="noun")
            
            session.add_card(card1)
            session.add_card(card2)
            
            # Should not raise exception
            show_session_summary(session)

    def test_displays_empty_session_summary(self):
        """Test that summary works with empty session."""
        session = Session()
        
        # Should not raise exception
        show_session_summary(session)