import tempfile
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from elevenlabs.client import AsyncElevenLabs

from audio import generate_audio, get_random_voice_id


@pytest.fixture
def elevenlabs_client():
    """Mock ElevenLabs client with typical responses."""
    client = MagicMock(spec=AsyncElevenLabs)

    # Mock voice
    mock_voice = MagicMock()
    mock_voice.name = "Maria (Mexican Spanish)"
    mock_voice.voice_id = "test-voice-id"

    # Mock search response
    mock_response = MagicMock()
    mock_response.voices = [mock_voice]

    # Mock API calls
    get_shared = AsyncMock(return_value=mock_response)
    client.voices = MagicMock(get_shared=get_shared)

    # Mock audio data as async iterator
    async def mock_audio_generator():
        for chunk in [b"audio", b"chunk", b"data"]:
            yield chunk

    convert = MagicMock(return_value=mock_audio_generator())
    client.text_to_speech = MagicMock(convert=convert)

    return client


class TestGetRandomVoiceId:
    def test_returns_valid_voice_id(self):
        """Test that get_random_voice_id returns a valid voice ID."""
        voice_id = get_random_voice_id()
        assert voice_id in [
            "CaJslL1xziwefCeTNzHv",
            "gbTn1bmCvNgk0QEAVyfM",
            "qXvyMc4erc4RzqXLpiiR",
        ]

    def test_multiple_calls_return_valid_voices(self):
        """Test that multiple calls consistently return valid voice IDs."""
        voice_ids = [get_random_voice_id() for _ in range(10)]
        valid_voices = [
            "CaJslL1xziwefCeTNzHv",
            "gbTn1bmCvNgk0QEAVyfM",
            "qXvyMc4erc4RzqXLpiiR",
        ]
        assert all(vid in valid_voices for vid in voice_ids)


class TestGenerateAudio:
    @pytest.mark.asyncio
    async def test_successful_generation(self, elevenlabs_client):
        """Test successful audio generation and file saving."""
        with (
            patch("audio.get_random_voice_id") as mock_get_voice_id,
            patch("builtins.open", mock_open()),
        ):
            mock_get_voice_id.return_value = "CaJslL1xziwefCeTNzHv"

            with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp_file:
                result = await generate_audio(elevenlabs_client, "hola", tmp_file.name)

                assert result == tmp_file.name
                elevenlabs_client.text_to_speech.convert.assert_called_once_with(
                    text="hola",
                    voice_id="CaJslL1xziwefCeTNzHv",
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )

    @pytest.mark.asyncio
    async def test_audio_generation_error(self, elevenlabs_client):
        """Test error handling during audio generation."""
        elevenlabs_client.text_to_speech.convert.side_effect = Exception("API Error")

        result = await generate_audio(elevenlabs_client, "hola", "test.mp3")

        assert result is None
