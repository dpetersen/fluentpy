import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from openai import OpenAI
from word_analysis import analyze_word


@pytest.fixture
def openai_client():
    json_response = json.dumps(
        {
            "ipa": "ˈo.la",
            "part_of_speech": "interjection",
            "gender": None,
            "verb_type": None,
        }
    )
    response = MagicMock(output_text=json_response)
    client = MagicMock(spec=OpenAI)

    create = AsyncMock(return_value=response)
    client.responses = MagicMock(create=create)

    return client


@pytest.mark.asyncio
async def test_analyze_word_interjection(openai_client):
    """Test analyzing an interjection"""
    result = await analyze_word(client=openai_client, word="hola")

    assert isinstance(result, dict)
    assert result["ipa"] == "ˈo.la"
    assert result["part_of_speech"] == "interjection"
    assert result["gender"] is None
    assert result["verb_type"] is None

    openai_client.responses.create.assert_called_once()
    assert (
        "the Spanish word 'hola'"
        in openai_client.responses.create.call_args.kwargs["input"]
    )


@pytest.mark.asyncio
async def test_analyze_word_noun_with_gender(openai_client):
    """Test analyzing a noun with gender"""
    json_response = json.dumps(
        {
            "ipa": "ˈka.sa",
            "part_of_speech": "noun",
            "gender": "feminine",
            "verb_type": None,
        }
    )
    openai_client.responses.create.return_value.output_text = json_response

    result = await analyze_word(client=openai_client, word="casa")

    assert result["ipa"] == "ˈka.sa"
    assert result["part_of_speech"] == "noun"
    assert result["gender"] == "feminine"
    assert result["verb_type"] is None


@pytest.mark.asyncio
async def test_analyze_word_verb_with_type(openai_client):
    """Test analyzing a verb with type"""
    json_response = json.dumps(
        {
            "ipa": "ko.ˈmeɾ",
            "part_of_speech": "verb",
            "gender": None,
            "verb_type": "transitive",
        }
    )
    openai_client.responses.create.return_value.output_text = json_response

    result = await analyze_word(client=openai_client, word="comer")

    assert result["ipa"] == "ko.ˈmeɾ"
    assert result["part_of_speech"] == "verb"
    assert result["gender"] is None
    assert result["verb_type"] == "transitive"


@pytest.mark.asyncio
async def test_analyze_word_invalid_json(openai_client):
    """Test handling invalid JSON response"""
    openai_client.responses.create.return_value.output_text = "Not valid JSON"

    with pytest.raises(ValueError, match="Invalid response format"):
        await analyze_word(client=openai_client, word="test")


@pytest.mark.asyncio
async def test_analyze_word_missing_fields(openai_client):
    """Test handling JSON with missing required fields"""
    json_response = json.dumps(
        {
            "ipa": "test",
            # missing part_of_speech
        }
    )
    openai_client.responses.create.return_value.output_text = json_response

    with pytest.raises(ValueError, match="Invalid response format"):
        await analyze_word(client=openai_client, word="test")
