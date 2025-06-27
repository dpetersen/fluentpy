"""Tests for sentence selection functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from models import ClozeCard
from review import select_sentences_for_cloze_card


class TestSelectSentencesForClozeCard:
    """Test the multi-select sentence functionality for Cloze cards."""

    @pytest.mark.asyncio
    async def test_select_multiple_sentences(self):
        """Test selecting multiple sentences returns correct tuples."""
        # Create a Cloze card with example sentences
        word_analysis = {
            "ipa": "ˈa.βlaɾ",
            "part_of_speech": "verb",
            "gender": None,
            "verb_type": "transitive",
            "example_sentences": [
                {"sentence": "Yo hablo español", "word_form": "hablo"},
                {"sentence": "Tú hablas muy bien", "word_form": "hablas"},
                {"sentence": "Ella habla con su madre", "word_form": "habla"},
            ],
        }

        card = ClozeCard(
            word="hablar",
            word_analysis=word_analysis,
        )

        # Mock questionary checkbox to select indices 0 and 2
        with patch("review.questionary.checkbox") as mock_checkbox:
            mock_checkbox_instance = AsyncMock()
            mock_checkbox_instance.ask_async.return_value = [
                0,
                2,
            ]  # Select first and third
            mock_checkbox.return_value = mock_checkbox_instance

            result = await select_sentences_for_cloze_card(card)

        # Verify the result
        assert len(result) == 2
        assert result[0] == ("Yo hablo español", "hablo")
        assert result[1] == ("Ella habla con su madre", "habla")

    @pytest.mark.asyncio
    async def test_select_single_sentence(self):
        """Test selecting a single sentence works correctly."""
        word_analysis = {
            "ipa": "ˈka.sa",
            "part_of_speech": "noun",
            "gender": "feminine",
            "verb_type": None,
            "example_sentences": [
                {"sentence": "La casa es grande", "word_form": "casa"},
                {"sentence": "Mi casa tiene jardín", "word_form": "casa"},
            ],
        }

        card = ClozeCard(
            word="casa",
            word_analysis=word_analysis,
        )

        # Mock questionary checkbox to select only index 1
        with patch("review.questionary.checkbox") as mock_checkbox:
            mock_checkbox_instance = AsyncMock()
            mock_checkbox_instance.ask_async.return_value = [1]
            mock_checkbox.return_value = mock_checkbox_instance

            result = await select_sentences_for_cloze_card(card)

        assert len(result) == 1
        assert result[0] == ("Mi casa tiene jardín", "casa")

    @pytest.mark.asyncio
    async def test_no_selection_prompts_single_select(self):
        """Test that no selection falls back to single select."""
        word_analysis = {
            "ipa": "koˈmeɾ",
            "part_of_speech": "verb",
            "gender": None,
            "verb_type": "transitive",
            "example_sentences": [
                {"sentence": "Voy a comer pizza", "word_form": "comer"},
                {"sentence": "Él come mucho", "word_form": "come"},
            ],
        }

        card = ClozeCard(
            word="comer",
            word_analysis=word_analysis,
        )

        # Mock questionary checkbox to return empty list (no selection)
        # and questionary select for fallback
        with (
            patch("review.questionary.checkbox") as mock_checkbox,
            patch("review.questionary.select") as mock_select,
        ):
            mock_checkbox_instance = AsyncMock()
            mock_checkbox_instance.ask_async.return_value = []  # No selection
            mock_checkbox.return_value = mock_checkbox_instance

            mock_select_instance = AsyncMock()
            mock_select_instance.ask_async.return_value = (
                "2. Él come mucho (uses: come)"
            )
            mock_select.return_value = mock_select_instance

            result = await select_sentences_for_cloze_card(card)

        assert len(result) == 1
        assert result[0] == ("Él come mucho", "come")

    @pytest.mark.asyncio
    async def test_create_duplicate_with_sentence(self):
        """Test the create_duplicate_with_sentence method."""
        word_analysis = {
            "ipa": "ˈa.βlaɾ",
            "part_of_speech": "verb",
            "gender": None,
            "verb_type": "transitive",
            "example_sentences": [],
        }

        original_card = ClozeCard(
            word="hablar",
            word_analysis=word_analysis,
            selected_sentence="Yo hablo español",
            selected_word_form="hablo",
            personal_context="My Spanish teacher",
            extra_prompt="classroom setting",
            memory_aid="to speak",
        )

        # Create duplicate with different sentence
        duplicate = original_card.create_duplicate_with_sentence(
            "Tú hablas muy bien", "hablas"
        )

        # Verify duplicate has same base data
        assert duplicate.word == original_card.word
        assert duplicate.word_analysis == original_card.word_analysis
        assert duplicate.personal_context == original_card.personal_context
        assert duplicate.extra_prompt == original_card.extra_prompt
        assert duplicate.memory_aid == original_card.memory_aid

        # Verify duplicate has different sentence and GUID
        assert duplicate.selected_sentence == "Tú hablas muy bien"
        assert duplicate.selected_word_form == "hablas"
        assert duplicate.guid != original_card.guid

        # Verify duplicate has no media paths and is not complete
        assert duplicate.image_path is None
        assert duplicate.audio_path is None
        assert duplicate.is_complete is False
