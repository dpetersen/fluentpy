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
                {"sentence": "Hola, ¿cómo estás?", "word_form": "Hola"},
                {"sentence": "Hola amigo, ¿qué tal?", "word_form": "Hola"},
                {"sentence": "Hola María, buenos días.", "word_form": "Hola"},
            ],
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
    sentences = [s["sentence"] for s in result["example_sentences"]]
    assert "Hola, ¿cómo estás?" in sentences

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
                {"sentence": "La casa es muy grande.", "word_form": "casa"},
                {"sentence": "Vivo en una casa blanca.", "word_form": "casa"},
                {"sentence": "Mi casa tiene jardín.", "word_form": "casa"},
                {"sentence": "Esta casa es nueva.", "word_form": "casa"},
                {"sentence": "La casa está vacía.", "word_form": "casa"},
                {"sentence": "Compramos una casa.", "word_form": "casa"},
                {"sentence": "Su casa es hermosa.", "word_form": "casa"},
                {"sentence": "La casa necesita pintura.", "word_form": "casa"},
                {"sentence": "Vendieron su casa.", "word_form": "casa"},
                {"sentence": "Esa casa es cara.", "word_form": "casa"},
            ],
        }
    )
    openai_client.responses.create.return_value.output_text = json_response

    result = await analyze_word(client=openai_client, word="casa")

    assert result["ipa"] == "ˈka.sa"
    assert result["part_of_speech"] == "noun"
    assert result["gender"] == "feminine"
    assert result["verb_type"] is None
    assert len(result["example_sentences"]) == 10
    sentences = [s["sentence"] for s in result["example_sentences"]]
    assert "La casa es muy grande." in sentences


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
                {"sentence": "Voy a comer una manzana.", "word_form": "comer"},
                {"sentence": "Ella come verduras.", "word_form": "come"},
                {"sentence": "Comemos juntos.", "word_form": "Comemos"},
                {"sentence": "¿Quieres comer pizza?", "word_form": "comer"},
                {"sentence": "No puedo comer más.", "word_form": "comer"},
                {"sentence": "Come despacio.", "word_form": "Come"},
                {"sentence": "Comió todo el pastel.", "word_form": "Comió"},
                {"sentence": "Van a comer en el restaurante.", "word_form": "comer"},
                {"sentence": "Comemos a las dos.", "word_form": "Comemos"},
                {"sentence": "Me gusta comer frutas.", "word_form": "comer"},
            ],
        }
    )
    openai_client.responses.create.return_value.output_text = json_response

    result = await analyze_word(client=openai_client, word="comer")

    assert result["ipa"] == "ko.ˈmeɾ"
    assert result["part_of_speech"] == "verb"
    assert result["gender"] is None
    assert result["verb_type"] == "transitive"
    assert len(result["example_sentences"]) == 10
    sentences = [s["sentence"] for s in result["example_sentences"]]
    assert "Voy a comer una manzana." in sentences


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
