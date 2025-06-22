import tempfile
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from elevenlabs.client import AsyncElevenLabs

from audio import generate_audio, get_mexican_spanish_voices


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


class TestGetMexicanSpanishVoices:
    @pytest.mark.asyncio
    async def test_success_first_search(self, elevenlabs_client):
        """Test successful retrieval with first search strategy."""
        voices = await get_mexican_spanish_voices(elevenlabs_client)

        assert len(voices) == 1
        assert voices[0].name == "Maria (Mexican Spanish)"
        # Should be called with shared voices search
        elevenlabs_client.voices.get_shared.assert_called_with(
            search="spanish"
        )

    @pytest.mark.asyncio
    async def test_fallback_to_general_search(self, elevenlabs_client):
        """Test fallback to general search when Mexican Spanish search fails."""
        general_voice = MagicMock()
        general_voice.name = "General Voice"
        general_voice.voice_id = "general-voice-id"

        mock_response_empty = MagicMock()
        mock_response_empty.voices = []
        
        mock_response_found = MagicMock()
        mock_response_found.voices = [general_voice]

        # Spanish shared search fails, general shared search succeeds
        elevenlabs_client.voices.get_shared.side_effect = [
            mock_response_empty,  # spanish shared search fails
            mock_response_found,  # general shared search succeeds
        ]

        voices = await get_mexican_spanish_voices(elevenlabs_client)

        assert len(voices) == 1
        assert voices[0].name == "General Voice"
        assert elevenlabs_client.voices.get_shared.call_count == 2

    @pytest.mark.asyncio
    async def test_no_voices_found(self, elevenlabs_client):
        """Test when no voices are found with any search strategy."""
        mock_response = MagicMock()
        mock_response.voices = []
        elevenlabs_client.voices.get_shared.return_value = mock_response

        voices = await get_mexican_spanish_voices(elevenlabs_client)

        assert len(voices) == 0

    @pytest.mark.asyncio
    async def test_general_fallback_with_limit(self, elevenlabs_client):
        """Test fallback to general voices with result limiting."""
        community_voice = MagicMock()
        community_voice.name = "Community Voice"
        community_voice.voice_id = "community-voice-id"
        
        mock_response_empty = MagicMock()
        mock_response_empty.voices = []
        
        mock_response_community = MagicMock()
        mock_response_community.voices = [community_voice] * 15  # 15 voices to test limit
        
        # Spanish shared search fails, then general shared fallback succeeds
        elevenlabs_client.voices.get_shared.side_effect = [
            mock_response_empty,  # spanish shared search fails
            mock_response_community,  # general shared fallback succeeds
        ]
        
        voices = await get_mexican_spanish_voices(elevenlabs_client)
        
        assert len(voices) == 10  # Should be limited to 10
        assert voices[0].name == "Community Voice"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, elevenlabs_client):
        """Test error handling when API calls fail."""
        elevenlabs_client.voices.get_shared.side_effect = Exception("API Error")

        voices = await get_mexican_spanish_voices(elevenlabs_client)

        assert len(voices) == 0


class TestGenerateAudio:
    @pytest.mark.asyncio
    async def test_successful_generation(self, elevenlabs_client):
        """Test successful audio generation and file saving."""
        with (
            patch("audio.get_mexican_spanish_voices") as mock_get_voices,
            patch("builtins.open", mock_open()),
        ):
            mock_voice = MagicMock()
            mock_voice.name = "Maria"
            mock_voice.voice_id = "test-voice-id"
            mock_get_voices.return_value = [mock_voice]

            with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp_file:
                result = await generate_audio(elevenlabs_client, "hola", tmp_file.name)

                assert result == tmp_file.name
                elevenlabs_client.text_to_speech.convert.assert_called_once_with(
                    text="hola",
                    voice_id="test-voice-id",
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )

    @pytest.mark.asyncio
    async def test_no_voices_available(self, elevenlabs_client):
        """Test when no Mexican Spanish voices are available."""
        with patch("audio.get_mexican_spanish_voices") as mock_get_voices:
            mock_get_voices.return_value = []

            result = await generate_audio(elevenlabs_client, "hola", "test.mp3")

            assert result is None

    @pytest.mark.asyncio
    async def test_audio_generation_error(self, elevenlabs_client):
        """Test error handling during audio generation."""
        with patch("audio.get_mexican_spanish_voices") as mock_get_voices:
            mock_voice = MagicMock()
            mock_voice.name = "Maria"
            mock_voice.voice_id = "test-voice-id"
            mock_get_voices.return_value = [mock_voice]

            elevenlabs_client.text_to_speech.convert.side_effect = Exception(
                "API Error"
            )

            result = await generate_audio(elevenlabs_client, "hola", "test.mp3")

            assert result is None
    
    @pytest.mark.asyncio
    async def test_audio_generation_tier_retry(self, elevenlabs_client):
        """Test retry logic when voice requires higher tier."""
        with patch("audio.get_mexican_spanish_voices") as mock_get_voices:
            voice1 = MagicMock()
            voice1.name = "Premium Voice"
            voice1.voice_id = "premium-id"
            
            voice2 = MagicMock()
            voice2.name = "Free Voice"
            voice2.voice_id = "free-id"
            
            mock_get_voices.return_value = [voice1, voice2]
            
            # First call fails with tier error, second succeeds
            async def mock_audio_generator():
                for chunk in [b"audio", b"data"]:
                    yield chunk
                    
            elevenlabs_client.text_to_speech.convert.side_effect = [
                Exception("status: 'free_users_not_allowed'"),
                mock_audio_generator()
            ]
            
            with patch("builtins.open", mock_open()):
                result = await generate_audio(elevenlabs_client, "hola", "test.mp3")
            
            assert result == "test.mp3"
            assert elevenlabs_client.text_to_speech.convert.call_count == 2
