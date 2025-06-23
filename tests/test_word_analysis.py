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
            "example_sentences": [
                "Hola, ¿cómo estás?",
                "Hola amigo, ¿qué tal?",
                "Hola María, buenos días."
            ]
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
    assert len(result["example_sentences"]) == 3
    assert "Hola, ¿cómo estás?" in result["example_sentences"]

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
            "example_sentences": [
                "La casa es muy grande.",
                "Vivo en una casa blanca.",
                "Mi casa tiene jardín.",
                "Esta casa es nueva.",
                "La casa está vacía.",
                "Compramos una casa.",
                "Su casa es hermosa.",
                "La casa necesita pintura.",
                "Vendieron su casa.",
                "Esa casa es cara."
            ]
        }
    )
    openai_client.responses.create.return_value.output_text = json_response

    result = await analyze_word(client=openai_client, word="casa")

    assert result["ipa"] == "ˈka.sa"
    assert result["part_of_speech"] == "noun"
    assert result["gender"] == "feminine"
    assert result["verb_type"] is None
    assert len(result["example_sentences"]) == 10
    assert "La casa es muy grande." in result["example_sentences"]


@pytest.mark.asyncio
async def test_analyze_word_verb_with_type(openai_client):
    """Test analyzing a verb with type"""
    json_response = json.dumps(
        {
            "ipa": "ko.ˈmeɾ",
            "part_of_speech": "verb",
            "gender": None,
            "verb_type": "transitive",
            "example_sentences": [
                "Voy a comer una manzana.",
                "Ella come verduras.",
                "Comemos juntos.",
                "¿Quieres comer pizza?",
                "No puedo comer más.",
                "Come despacio.",
                "Comió todo el pastel.",
                "Van a comer en el restaurante.",
                "Comemos a las dos.",
                "Me gusta comer frutas."
            ]
        }
    )
    openai_client.responses.create.return_value.output_text = json_response

    result = await analyze_word(client=openai_client, word="comer")

    assert result["ipa"] == "ko.ˈmeɾ"
    assert result["part_of_speech"] == "verb"
    assert result["gender"] is None
    assert result["verb_type"] == "transitive"
    assert len(result["example_sentences"]) == 10
    assert "Voy a comer una manzana." in result["example_sentences"]


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
