import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from mnemonic_images import (
    get_mnemonic_filename,
    check_mnemonic_exists,
    _create_mnemonic_prompt,
    generate_mnemonic_image,
)


class TestGetMnemonicFilename:
    def test_simple_word(self):
        """Test filename generation for simple word."""
        assert get_mnemonic_filename("casa") == "mpi-casa.jpg"

    def test_uppercase_word(self):
        """Test filename generation normalizes to lowercase."""
        assert get_mnemonic_filename("CASA") == "mpi-casa.jpg"

    def test_phrase_with_spaces(self):
        """Test filename generation replaces spaces with underscores."""
        assert get_mnemonic_filename("de hecho") == "mpi-de_hecho.jpg"

    def test_complex_phrase(self):
        """Test filename generation for complex phrase."""
        assert get_mnemonic_filename("De Hecho") == "mpi-de_hecho.jpg"


class TestCheckMnemonicExists:
    def test_file_exists(self, tmp_path):
        """Test checking when mnemonic file exists."""
        # Create test file
        mnemonic_file = tmp_path / "mpi-casa.jpg"
        mnemonic_file.write_text("fake image")

        assert check_mnemonic_exists("casa", tmp_path) is True

    def test_file_not_exists(self, tmp_path):
        """Test checking when mnemonic file doesn't exist."""
        assert check_mnemonic_exists("casa", tmp_path) is False

    def test_different_word_forms(self, tmp_path):
        """Test that word is normalized before checking."""
        # Create test file
        mnemonic_file = tmp_path / "mpi-casa.jpg"
        mnemonic_file.write_text("fake image")

        # Should find the file even with different case
        assert check_mnemonic_exists("CASA", tmp_path) is True
        assert check_mnemonic_exists("Casa", tmp_path) is True


class TestCreateMnemonicPrompt:
    def test_creates_prompt_with_description(self):
        """Test prompt creation includes word and description."""
        prompt = _create_mnemonic_prompt("dormir", "college dorm room")

        assert "dormir" in prompt
        assert "college dorm room" in prompt
        assert "phonetic similarity" in prompt
        assert "NOT contain any text" in prompt

    def test_prompt_structure(self):
        """Test prompt has correct structure and instructions."""
        prompt = _create_mnemonic_prompt("comer", "comet in space")

        # Check key instructions are present
        assert "memorable image" in prompt
        assert "sound association" in prompt
        assert "Spanish word 'comer'" in prompt
        assert "comet in space" in prompt


class TestGenerateMnemonicImage:
    @pytest.mark.asyncio
    async def test_successful_generation(self, tmp_path):
        """Test successful mnemonic image generation."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="aW1hZ2VkYXRh")]  # base64 "imagedata"
        mock_client.images.generate.return_value = mock_response

        output_path = tmp_path / "test.jpg"

        result = await generate_mnemonic_image(
            client=mock_client,
            word="dormir",
            description="dorm room",
            output_path=output_path,
        )

        # Check API was called correctly
        mock_client.images.generate.assert_called_once()
        call_args = mock_client.images.generate.call_args[1]
        assert "dormir" in call_args["prompt"]
        assert "dorm room" in call_args["prompt"]

        # Check file was created
        assert output_path.exists()
        assert result == output_path

    @pytest.mark.asyncio
    async def test_generation_failure(self, tmp_path):
        """Test handling of image generation failure."""
        mock_client = AsyncMock()
        mock_client.images.generate.side_effect = Exception("API Error")

        output_path = tmp_path / "test.jpg"

        with pytest.raises(Exception, match="API Error"):
            await generate_mnemonic_image(
                client=mock_client,
                word="dormir",
                description="dorm room",
                output_path=output_path,
            )

        # File should not be created
        assert not output_path.exists()

    @pytest.mark.asyncio
    async def test_no_image_data(self, tmp_path):
        """Test handling when API returns no image data."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = []  # No image data
        mock_client.images.generate.return_value = mock_response

        output_path = tmp_path / "test.jpg"

        with pytest.raises(RuntimeError, match="No image data received"):
            await generate_mnemonic_image(
                client=mock_client,
                word="dormir",
                description="dorm room",
                output_path=output_path,
            )
