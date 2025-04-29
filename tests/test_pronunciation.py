import pytest
from unittest.mock import MagicMock

from openai import OpenAI
from pronunciation import get_pronunciation


@pytest.fixture
def openai_client():
    client = MagicMock(spec=OpenAI)
    response = MagicMock(output_text="ˈo.la")

    client.responses = MagicMock()
    client.responses.create.return_value = response

    return client


def test_get_pronunciation(openai_client):
    """tests OpenAI is called and its results returned"""
    result = get_pronunciation(client=openai_client, word="hola")
    assert result == "ˈo.la"

    openai_client.responses.create.assert_called_once()
    assert (
        "the Spanish word 'hola'"
        in openai_client.responses.create.call_args.kwargs["input"]
    )
