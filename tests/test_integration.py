import csv
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from main import main
from models import Session


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with typical responses for integration tests."""
    client = MagicMock()

    # Mock word analysis responses
    def create_word_analysis_response(word, part_of_speech="noun", gender="masculine"):
        """Create a mock word analysis response."""
        base_response = {
            "ipa": f"/{word}/",
            "part_of_speech": part_of_speech,
            "gender": gender if part_of_speech == "noun" else None,
            "verb_type": "transitive" if part_of_speech == "verb" else None,
            "example_sentences": [],
        }

        # Add example sentences for cloze cards
        if part_of_speech == "verb":
            base_response["example_sentences"] = [
                {
                    "sentence": f"Yo {word} todos los días.",
                    "word_form": word,
                    "ipa": f"/{word}/",
                    "tense": "presente",
                },
                {
                    "sentence": f"Ella {word}ó ayer.",
                    "word_form": f"{word}ó",
                    "ipa": f"/{word}o/",
                    "tense": "pretérito",
                },
            ]

        mock_response = MagicMock()
        mock_response.output_text = json.dumps(base_response)
        return mock_response

    # Setup responses.create mock
    async def mock_create(**kwargs):
        input_text = kwargs.get("input", "")
        # Extract word from the analysis prompt
        if "Analyze the Spanish word '" in input_text:
            word = input_text.split("Analyze the Spanish word '")[1].split("'")[0]
        else:
            word = "test"

        # Define test word characteristics
        word_configs = {
            "casa": ("noun", "feminine"),
            "perro": ("noun", "masculine"),
            "hablar": ("verb", None),
            "correr": ("verb", None),
        }

        part_of_speech, gender = word_configs.get(word, ("noun", "masculine"))
        return create_word_analysis_response(word, part_of_speech, gender)

    client.responses.create = AsyncMock(side_effect=mock_create)

    # Mock image generation
    async def mock_image_generate(**kwargs):
        mock_response = MagicMock()
        # Create a mock data object with b64_json attribute
        mock_data = MagicMock()
        mock_data.b64_json = "aW1hZ2VkYXRh"  # "imagedata" in base64
        mock_response.data = [mock_data]
        return mock_response

    client.images.generate = AsyncMock(side_effect=mock_image_generate)

    return client


@pytest.fixture
def mock_elevenlabs_client():
    """Mock ElevenLabs client for audio generation."""
    client = MagicMock()

    # Mock voices.get_shared
    voices = [MagicMock(name="Mexican Spanish Voice", labels={"language": "es-MX"})]
    client.voices.get_shared = AsyncMock(return_value=MagicMock(voices=voices))

    # Mock text_to_speech.convert
    def mock_convert(**kwargs):
        # Return async generator for audio chunks
        async def async_gen():
            yield b"mock audio data chunk 1"
            yield b"mock audio data chunk 2"

        return async_gen()

    # Create a mock object for text_to_speech with the convert method
    mock_text_to_speech = MagicMock()
    mock_text_to_speech.convert = MagicMock(side_effect=mock_convert)
    client.text_to_speech = mock_text_to_speech

    return client


@pytest.fixture
def word_file(tmp_path):
    """Create a temporary word file for testing."""
    word_file = tmp_path / "test_words.txt"
    word_file.write_text("casa\nperro\n")
    return word_file


@pytest.fixture
def cloze_file(tmp_path):
    """Create a temporary cloze word file for testing."""
    cloze_file = tmp_path / "test_cloze.txt"
    cloze_file.write_text("hablar\ncorrer\n")
    return cloze_file


@pytest.fixture
def mock_anki_path(tmp_path):
    """Mock Anki collection.media path."""
    media_path = tmp_path / "collection.media"
    media_path.mkdir()
    return media_path


def validate_csv_format(csv_path: Path, expected_note_type: str):
    """Validate that the CSV file has the correct Anki format."""
    assert csv_path.exists(), f"CSV file not found: {csv_path}"

    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.strip().split("\n")

        # Check for required header lines
        header_lines = [line for line in lines if line.startswith("#")]

        # Check for #fields: header
        assert any(line.startswith("#fields:") for line in header_lines), (
            "CSV must contain #fields: header"
        )

        # Check note type comment
        assert f"#notetype:{expected_note_type}" in header_lines, (
            f"Missing note type: {expected_note_type}"
        )

        # Parse CSV data (skip comment lines)
        csv_lines = [line for line in lines if not line.startswith("#")]
        if csv_lines:
            reader = csv.reader(csv_lines)
            rows = list(reader)
            assert len(rows) > 0, "CSV should contain data rows"

    return True


def validate_media_files(session: Session, media_dir: Path):
    """Validate that media files were created correctly."""
    for card in session.cards:
        if card.image_path:
            # Check original path exists
            image_path = (
                Path(card.image_path)
                if isinstance(card.image_path, str)
                else card.image_path
            )
            assert image_path is not None and image_path.exists(), (
                f"Image not found: {image_path}"
            )

            # Check media file was copied with UUID naming
            media_filename = f"{card.word}-{card.guid[:8]}.jpg"
            media_path = media_dir / media_filename
            assert media_path.exists(), f"Media file not copied: {media_filename}"

        if card.audio_path:
            # Check original path exists
            audio_path = (
                Path(card.audio_path)
                if isinstance(card.audio_path, str)
                else card.audio_path
            )
            assert audio_path is not None and audio_path.exists(), (
                f"Audio not found: {audio_path}"
            )

            # Check media file was copied
            media_filename = f"{card.word}-{card.guid[:8]}.mp3"
            media_path = media_dir / media_filename
            assert media_path.exists(), f"Media file not copied: {media_filename}"


class TestIntegration:
    """Integration tests for the complete FluentPy workflow."""

    @pytest.mark.asyncio
    @patch("main.check_mpv_availability")
    @patch("sys.argv")
    @patch("session.AsyncOpenAI")
    @patch("session.AsyncElevenLabs")
    @patch("config.find_anki_collection_media")
    @patch("review.subprocess.run")
    @patch("review.view_image")
    @patch("anki_export.shutil.copy2")
    @patch("session.Path")
    async def test_vocabulary_only_workflow(
        self,
        mock_path_cls,
        mock_copy2,
        mock_view_image,
        mock_subprocess_run,
        mock_find_anki_media,
        mock_elevenlabs_cls,
        mock_openai_cls,
        mock_argv,
        mock_mpv_check,
        mock_openai_client,
        mock_elevenlabs_client,
        word_file,
        mock_anki_path,
        tmp_path,
    ):
        """Test creating vocabulary cards only."""
        # Create a test output directory
        test_output_dir = tmp_path / "test_output"
        test_output_dir.mkdir()

        # Mock Path to use our test directory
        def mock_path_init(path_str):
            if path_str == "./output":
                return test_output_dir
            return Path(path_str)

        mock_path_cls.side_effect = mock_path_init

        # Setup mocks
        mock_mpv_check.return_value = True
        mock_argv.__len__.return_value = 4
        mock_argv.__getitem__.side_effect = lambda x: [
            "main.py",
            "--word-file",
            str(word_file),
            "--auto-approve",
        ][x]
        mock_openai_cls.return_value = mock_openai_client
        mock_elevenlabs_cls.return_value = mock_elevenlabs_client
        mock_find_anki_media.return_value = mock_anki_path

        # Mock subprocess for audio playback
        mock_subprocess_run.return_value.returncode = 0

        # Mock file copy to prevent actual copying to Anki
        def mock_copy_side_effect(src, dst):
            # Create a dummy file at destination to simulate copy
            Path(dst).touch()

        mock_copy2.side_effect = mock_copy_side_effect

        # Run the main function
        await main()

        # Validate outputs
        # CSV file should be created in test output directory
        assert test_output_dir.exists(), "Test output directory should exist"

        csv_files = list(test_output_dir.glob("anki_import.csv"))
        assert len(csv_files) == 1, "Should have exactly one vocabulary CSV"

        validate_csv_format(csv_files[0], "2. Picture Words")

        # Check media files were copied to Anki media path
        mp3_files = list(mock_anki_path.glob("*.mp3"))

        # Audio files should be copied
        assert len(mp3_files) == 2, f"Should have 2 audio files, found {len(mp3_files)}"

    @pytest.mark.asyncio
    @patch("main.check_mpv_availability")
    @patch("sys.argv")
    @patch("session.AsyncOpenAI")
    @patch("session.AsyncElevenLabs")
    @patch("config.find_anki_collection_media")
    @patch("review.subprocess.run")
    @patch("review.view_image")
    @patch("cloze_export.shutil.copy2")
    @patch("session.Path")
    async def test_cloze_workflow(
        self,
        mock_path_cls,
        mock_copy2,
        mock_view_image,
        mock_subprocess_run,
        mock_find_anki_media,
        mock_elevenlabs_cls,
        mock_openai_cls,
        mock_argv,
        mock_mpv_check,
        mock_openai_client,
        mock_elevenlabs_client,
        cloze_file,
        mock_anki_path,
        tmp_path,
    ):
        """Test creating cloze cards with sentence selection."""
        # Create a test output directory
        test_output_dir = tmp_path / "test_output"
        test_output_dir.mkdir()

        # Mock Path to use our test directory
        def mock_path_init(path_str):
            if path_str == "./output":
                return test_output_dir
            return Path(path_str)

        mock_path_cls.side_effect = mock_path_init

        # Setup mocks
        mock_mpv_check.return_value = True
        mock_argv.__len__.return_value = 4
        mock_argv.__getitem__.side_effect = lambda x: [
            "main.py",
            "--cloze-file",
            str(cloze_file),
            "--auto-approve",
        ][x]
        mock_openai_cls.return_value = mock_openai_client
        mock_elevenlabs_cls.return_value = mock_elevenlabs_client
        mock_find_anki_media.return_value = mock_anki_path

        # Mock subprocess for audio playback
        mock_subprocess_run.return_value.returncode = 0

        # Mock file copy to prevent actual copying to Anki
        def mock_copy_side_effect(src, dst):
            # Create a dummy file at destination to simulate copy
            Path(dst).touch()

        mock_copy2.side_effect = mock_copy_side_effect

        # Run the main function
        await main()

        # Validate outputs
        # CSV file should be created in test output directory
        assert test_output_dir.exists(), "Test output directory should exist"

        csv_files = list(test_output_dir.glob("anki_import_cloze.csv"))
        assert len(csv_files) == 1, "Should have exactly one cloze CSV"

        validate_csv_format(csv_files[0], "3. All-Purpose Card")

        # Check media files were copied to Anki media path
        jpg_files = list(mock_anki_path.glob("*.jpg"))
        mp3_files = list(mock_anki_path.glob("*.mp3"))
        # Should have at least 2 images and 2 audio files (one per cloze card)
        assert len(jpg_files) >= 2, (
            f"Should have at least 2 images, found {len(jpg_files)}"
        )
        assert len(mp3_files) >= 2, (
            f"Should have at least 2 audio files, found {len(mp3_files)}"
        )
