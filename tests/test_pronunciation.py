import pytest
from unittest.mock import AsyncMock, MagicMock

from openai import OpenAI
from pronunciation import get_pronunciation


@pytest.fixture
def openai_client():
    response = MagicMock(output_text="ˈo.la")
    client = MagicMock(spec=OpenAI)

    create = AsyncMock(return_value=response)
    client.responses = MagicMock(create=create)

    return client


@pytest.mark.asyncio
async def test_get_pronunciation(openai_client):
    """tests OpenAI is called and its results returned"""
    result = await get_pronunciation(client=openai_client, word="hola")
    assert result == "ˈo.la"

    openai_client.responses.create.assert_called_once()
    assert (
        "the Spanish word 'hola'"
        in openai_client.responses.create.call_args.kwargs["input"]
    )
