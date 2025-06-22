import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from models import Session, WordCard
from review import (
    display_card_media,
    handle_audio_regeneration,
    handle_audio_replay,
    handle_image_regeneration,
    play_audio,
    review_card,
    show_session_summary,
)


class TestPlayAudio:
    @patch("review.subprocess.run")
    def test_plays_audio_successfully(self, mock_run):
        """Test successful audio playback."""
        audio_path = Path("/tmp/test.mp3")

        # Mock successful mpv execution
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        play_audio(audio_path)

        mock_run.assert_called_once_with(
            [
                "mpv",
                "--really-quiet",
                "--no-video",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("review.subprocess.run")
    def test_handles_mpv_error_gracefully(self, mock_run):
        """Test that mpv errors are handled without raising."""
        audio_path = Path("/tmp/test.mp3")

        # Mock mpv error
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "File not found"

        # Should not raise exception
        play_audio(audio_path)

    @patch("review.subprocess.run")
    def test_handles_mpv_not_found(self, mock_run):
        """Test handling when mpv is not installed."""
        audio_path = Path("/tmp/test.mp3")

        # Mock mpv not found
        mock_run.side_effect = FileNotFoundError("mpv not found")

        # Should not raise exception
        play_audio(audio_path)

    @patch("review.subprocess.run")
    def test_handles_timeout(self, mock_run):
        """Test handling of playback timeout."""
        audio_path = Path("/tmp/test.mp3")

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("mpv", 30)

        # Should not raise exception
        play_audio(audio_path)


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
    @patch("review.play_audio")
    async def test_plays_audio_when_available(self, mock_play_audio):
        """Test that audio is played when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.touch()

            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", audio_path=audio_path
            )

            await display_card_media(card)

            mock_play_audio.assert_called_once_with(audio_path)


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

        mock_text.return_value.ask_async = AsyncMock(return_value="make it colorful")
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

        mock_text.return_value.ask_async = AsyncMock(return_value="")
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

        mock_text.return_value.ask_async = AsyncMock(return_value="")
        mock_regen.return_value = False

        # Should not raise exception
        await handle_image_regeneration(session, card)


class TestHandleAudioRegeneration:
    @pytest.mark.asyncio
    @patch("review.play_audio")
    @patch("review.regenerate_audio")
    async def test_regenerates_audio_successfully(self, mock_regen, mock_play):
        """Test successful audio regeneration plays the new audio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session()
            audio_path = Path(tmpdir) / "new_audio.mp3"
            audio_path.touch()
            card = WordCard(word="hola", ipa="ˈo.la", part_of_speech="interjection")
            card.audio_path = audio_path

            mock_regen.return_value = True

            await handle_audio_regeneration(session, card)

            mock_regen.assert_called_once_with(session, card)
            mock_play.assert_called_once_with(audio_path)

    @pytest.mark.asyncio
    @patch("review.regenerate_audio")
    async def test_handles_regeneration_failure(self, mock_regen):
        """Test handling of audio regeneration failure."""
        session = Session()
        card = WordCard(word="hola", ipa="ˈo.la", part_of_speech="interjection")

        mock_regen.return_value = False

        # Should not raise exception
        await handle_audio_regeneration(session, card)


class TestHandleAudioReplay:
    @pytest.mark.asyncio
    @patch("review.play_audio")
    async def test_replays_audio_when_available(self, mock_play):
        """Test audio replay when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.touch()
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", audio_path=audio_path
            )

            await handle_audio_replay(card)

            mock_play.assert_called_once_with(audio_path)

    @pytest.mark.asyncio
    async def test_handles_missing_audio_gracefully(self):
        """Test handling when no audio file exists."""
        card = WordCard(word="test", ipa="test", part_of_speech="noun")

        # Should not raise exception
        await handle_audio_replay(card)


class TestReviewCard:
    @pytest.mark.asyncio
    @patch("review.display_card_media")
    @patch("review.questionary.select")
    async def test_approves_card(self, mock_select, mock_display):
        """Test approving a card marks it complete."""
        session = Session()
        card = WordCard(word="test", ipa="test", part_of_speech="noun")

        mock_select.return_value.ask_async = AsyncMock(
            return_value="✅ Approve this card"
        )

        await review_card(session, card)

        assert card.is_complete is True

    @pytest.mark.asyncio
    @patch("review.handle_image_regeneration")
    @patch("review.display_card_media")
    @patch("review.questionary.select")
    async def test_regenerates_image(
        self, mock_select, mock_display, mock_handle_image
    ):
        """Test that image regeneration option calls handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session()
            image_path = Path(tmpdir) / "test.jpg"
            image_path.touch()
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", image_path=image_path
            )

            # First call regenerate, then approve
            mock_select.return_value.ask_async = AsyncMock(
                side_effect=[
                    "🖼️  Regenerate image",
                    "✅ Approve this card",
                ]
            )

            await review_card(session, card)

            mock_handle_image.assert_called_once_with(session, card)

    @pytest.mark.asyncio
    @patch("review.handle_audio_regeneration")
    @patch("review.display_card_media")
    @patch("review.questionary.select")
    async def test_regenerates_audio(
        self, mock_select, mock_display, mock_handle_audio
    ):
        """Test that audio regeneration option calls handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session()
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.touch()
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", audio_path=audio_path
            )

            # First call regenerate, then approve
            mock_select.return_value.ask_async = AsyncMock(
                side_effect=[
                    "🔊 Regenerate audio",
                    "✅ Approve this card",
                ]
            )

            await review_card(session, card)

            mock_handle_audio.assert_called_once_with(session, card)

    @pytest.mark.asyncio
    @patch("review.handle_audio_replay")
    @patch("review.display_card_media")
    @patch("review.questionary.select")
    async def test_replays_audio(self, mock_select, mock_display, mock_handle_replay):
        """Test that audio replay option calls handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = Session()
            audio_path = Path(tmpdir) / "test.mp3"
            audio_path.touch()
            card = WordCard(
                word="test", ipa="test", part_of_speech="noun", audio_path=audio_path
            )

            # First call replay, then approve
            mock_select.return_value.ask_async = AsyncMock(
                side_effect=[
                    "🔈 Replay audio",
                    "✅ Approve this card",
                ]
            )

            await review_card(session, card)

            mock_handle_replay.assert_called_once_with(card)


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
