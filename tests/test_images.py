import base64
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import OpenAI

from images import generate_image, _create_prompt
from word_analysis import WordAnalysis


@pytest.fixture
def openai_client():
    expected = "I am test data"
    expected_encoded = base64.b64encode(expected.encode("utf-8")).decode("utf-8")

    client = MagicMock(spec=OpenAI)
    response = MagicMock()
    response.data = [MagicMock(b64_json=expected_encoded)]

    generate = AsyncMock(return_value=response)
    client.images = MagicMock(generate=generate)

    return client


@pytest.mark.asyncio
async def test_generate_image(openai_client):
    """tests that OpenAI is called correctly and the passed-in path is written to"""
    analysis: WordAnalysis = {
        "ipa": "ˈo.la",
        "part_of_speech": "interjection",
        "gender": None,
        "verb_type": None,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        desired_path = os.path.join(tmpdir, "hola.png")
        result_path = await generate_image(
            client=openai_client, word="hola", analysis=analysis, path=desired_path
        )
        assert result_path == desired_path
        assert open(desired_path, "rb").read() == b"I am test data"

        openai_client.images.generate.assert_called_once()
        call_args = openai_client.images.generate.call_args
        assert call_args.kwargs["model"] == "gpt-image-1"


class TestCreatePrompt:
    def test_verb_prompt_includes_action_emphasis(self):
        """Test that verb prompts emphasize action"""
        analysis: WordAnalysis = {
            "ipa": "koˈmer",
            "part_of_speech": "verb",
            "gender": None,
            "verb_type": "transitive",
        }

        prompt = _create_prompt("comer", analysis)

        assert "clear action happening" in prompt.lower()
        assert "action should be prominent" in prompt.lower()
        assert "verb" in prompt.lower()

    def test_adjective_prompt_includes_multiple_objects(self):
        """Test that adjective prompts show multiple objects with the same property"""
        analysis: WordAnalysis = {
            "ipa": "aˈθul",
            "part_of_speech": "adjective",
            "gender": None,
            "verb_type": None,
        }

        prompt = _create_prompt("azul", analysis)

        assert "multiple different objects" in prompt.lower()
        assert "adjective" in prompt.lower()
        assert (
            "blue hair" in prompt.lower()
            and "blue car" in prompt.lower()
            and "blue bike" in prompt.lower()
        )

    def test_masculine_noun_prompt_includes_intense_fire_heat(self):
        """Test that masculine nouns include intense fire/heat imagery"""
        analysis: WordAnalysis = {
            "ipa": "ˈli.βɾo",
            "part_of_speech": "noun",
            "gender": "masculine",
            "verb_type": None,
        }

        prompt = _create_prompt("libro", analysis)

        assert "masculine" in prompt.lower()
        assert any(
            term in prompt.lower()
            for term in [
                "blazing flames",
                "intense heat",
                "burning",
                "fiery",
                "dramatically hot",
            ]
        )

    def test_feminine_noun_prompt_includes_intense_ice_cold(self):
        """Test that feminine nouns include intense ice/cold imagery"""
        analysis: WordAnalysis = {
            "ipa": "ˈka.sa",
            "part_of_speech": "noun",
            "gender": "feminine",
            "verb_type": None,
        }

        prompt = _create_prompt("casa", analysis)

        assert "feminine" in prompt.lower()
        assert any(
            term in prompt.lower()
            for term in [
                "freezing ice",
                "bitter cold",
                "frost",
                "blizzards",
                "arctic",
                "dramatically cold",
                "freezing",
            ]
        )

    def test_noun_without_gender_uses_generic_prompt(self):
        """Test that nouns without gender get generic prompts"""
        analysis: WordAnalysis = {
            "ipa": "ˈa.ɣwa",
            "part_of_speech": "noun",
            "gender": None,
            "verb_type": None,
        }

        prompt = _create_prompt("agua", analysis)

        assert "clear, memorable image" in prompt.lower()
        # Should not contain gender-specific imagery
        assert not any(
            term in prompt.lower()
            for term in [
                "fire",
                "heat",
                "ice",
                "frozen",
                "flames",
                "burning",
                "fiery",
                "freezing",
                "blizzard",
                "arctic",
            ]
        )

    def test_other_parts_of_speech_use_generic_prompt(self):
        """Test that other parts of speech get generic prompts"""
        analysis: WordAnalysis = {
            "ipa": "ˈo.la",
            "part_of_speech": "interjection",
            "gender": None,
            "verb_type": None,
        }

        prompt = _create_prompt("hola", analysis)

        assert "clear, memorable image" in prompt.lower()
        # Should not contain specific grammar prompts
        assert "action" not in prompt.lower()
        assert "multiple objects" not in prompt.lower()

    def test_all_prompts_include_base_instructions(self):
        """Test that all prompts include the base flashcard instructions"""
        analysis: WordAnalysis = {
            "ipa": "test",
            "part_of_speech": "verb",
            "gender": None,
            "verb_type": None,
        }

        prompt = _create_prompt("test", analysis)

        assert "anki flashcards" in prompt.lower()
        assert (
            "word i give you" in prompt.lower()
            and "should not appear" in prompt.lower()
        )
        assert "mexican" in prompt.lower()
        assert "the word is: test" in prompt.lower()

    def test_extra_prompt_is_included(self):
        """Test that extra prompt is included when provided"""
        analysis: WordAnalysis = {
            "ipa": "ˈka.sa",
            "part_of_speech": "noun",
            "gender": "feminine",
            "verb_type": None,
        }
        
        extra_prompt = "make it colorful with bright flowers"
        prompt = _create_prompt("casa", analysis, extra_prompt)
        
        assert "Additional context: make it colorful with bright flowers" in prompt
        # Should still include base instructions
        assert "anki flashcards" in prompt.lower()
        # Should still include gender-specific instructions for feminine noun
        assert any(
            term in prompt.lower()
            for term in ["freezing", "cold", "ice", "arctic"]
        )

    def test_no_extra_prompt_works_normally(self):
        """Test that prompt works normally when no extra prompt provided"""
        analysis: WordAnalysis = {
            "ipa": "ˈka.sa", 
            "part_of_speech": "noun",
            "gender": "feminine",
            "verb_type": None,
        }
        
        prompt = _create_prompt("casa", analysis)
        
        assert "Additional context:" not in prompt
        # Should still include base and gender-specific instructions
        assert "anki flashcards" in prompt.lower()
        assert any(
            term in prompt.lower()
            for term in ["freezing", "cold", "ice", "arctic"]
        )
