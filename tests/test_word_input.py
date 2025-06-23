from unittest.mock import AsyncMock, patch

import pytest

from models import WordInput
from word_input import get_all_word_inputs, get_words_from_list


class TestGetWordInputs:
    @pytest.mark.asyncio
    @patch("word_input.questionary.text")
    async def test_single_word_no_metadata(self, mock_text):
        """Test collecting a single word without optional fields."""
        # Mock the sequence of text inputs
        mock_text.return_value.ask_async = AsyncMock(
            side_effect=[
                "hola",  # word
                "",  # personal context (empty)
                "",  # extra image prompt (empty)
                "",  # next word (finish vocabulary)
                "",  # next word (finish cloze)
            ]
        )

        vocabulary, cloze = await get_all_word_inputs()
        result = vocabulary

        assert len(result) == 1
        assert result[0].word == "hola"
        assert result[0].personal_context is None
        assert result[0].extra_image_prompt is None

    @pytest.mark.asyncio
    @patch("word_input.questionary.text")
    async def test_single_word_with_metadata(self, mock_text):
        """Test collecting a word with all optional fields."""
        mock_text.return_value.ask_async = AsyncMock(
            side_effect=[
                "correr",  # word
                "I run every morning",  # personal context
                "person running in sunny park",  # extra image prompt
                "",  # next word (finish vocabulary)
                "",  # next word (finish cloze)
            ]
        )

        vocabulary, cloze = await get_all_word_inputs()
        result = vocabulary

        assert len(result) == 1
        assert result[0].word == "correr"
        assert result[0].personal_context == "I run every morning"
        assert result[0].extra_image_prompt == "person running in sunny park"

    @pytest.mark.asyncio
    @patch("word_input.questionary.text")
    async def test_multiple_words(self, mock_text):
        """Test collecting multiple words with mixed metadata."""
        mock_text.return_value.ask_async = AsyncMock(
            side_effect=[
                "gato",  # word 1
                "My neighbor has one",  # context 1
                "",  # no image prompt 1
                "perro",  # word 2
                "",  # no context 2
                "golden retriever",  # image prompt 2
                "",  # finish vocabulary
                "",  # finish cloze
            ]
        )

        vocabulary, cloze = await get_all_word_inputs()
        result = vocabulary

        assert len(result) == 2
        assert result[0].word == "gato"
        assert result[0].personal_context == "My neighbor has one"
        assert result[0].extra_image_prompt is None
        assert result[1].word == "perro"
        assert result[1].personal_context is None
        assert result[1].extra_image_prompt == "golden retriever"

    @pytest.mark.asyncio
    @patch("word_input.questionary.text")
    async def test_word_normalization(self, mock_text):
        """Test that words are normalized to lowercase and trimmed."""
        mock_text.return_value.ask_async = AsyncMock(
            side_effect=[
                "  CASA  ",  # word with spaces and caps
                "  My home  ",  # context with spaces
                "  ",  # whitespace-only image prompt
                "",  # finish vocabulary
                "",  # finish cloze
            ]
        )

        vocabulary, cloze = await get_all_word_inputs()
        result = vocabulary

        assert len(result) == 1
        assert result[0].word == "casa"
        assert result[0].personal_context == "My home"
        assert result[0].extra_image_prompt is None


class TestGetWordsFromList:
    def test_simple_word_list(self):
        """Test converting a list of words to WordInput objects."""
        words = ["hola", "adiós", "gracias"]
        result = get_words_from_list(words)

        assert len(result) == 3
        assert all(isinstance(w, WordInput) for w in result)
        assert [w.word for w in result] == ["hola", "adiós", "gracias"]
        assert all(w.personal_context is None for w in result)
        assert all(w.extra_image_prompt is None for w in result)

    def test_word_list_normalization(self):
        """Test that words from list are normalized."""
        words = ["  CASA  ", "Perro", " gato "]
        result = get_words_from_list(words)

        assert len(result) == 3
        assert [w.word for w in result] == ["casa", "perro", "gato"]

    def test_empty_strings_filtered(self):
        """Test that empty strings are filtered out."""
        words = ["hola", "", "  ", "adiós", "   "]
        result = get_words_from_list(words)

        assert len(result) == 2
        assert [w.word for w in result] == ["hola", "adiós"]

    def test_empty_list(self):
        """Test handling of empty word list."""
        result = get_words_from_list([])
        assert result == []
