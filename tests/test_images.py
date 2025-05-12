import base64
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import OpenAI

from images import generate_image


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
    with tempfile.TemporaryDirectory() as tmpdir:
        desired_path = os.path.join(tmpdir, "hola.png")
        await generate_image(client=openai_client, word="hola", path=desired_path)
        assert open(desired_path, "rb").read() == b"I am test data"
