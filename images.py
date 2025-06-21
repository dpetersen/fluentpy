import base64

from loguru import logger
from openai import AsyncOpenAI
from term_image.image import from_file

PROMPT_TEMPLATE = """
I am making memorable Anki flashcards for Spanish vocabulary. I am using the mneumonic imagery that male words are on fire and female words are frozen, or cold.

It is absolutely critical that the word I give you, or any similar words, SHOULD NOT appear in the image. I am looking for imagery, not traditional flash cards. The style of the image can be whatever style you think best fits the word.

I'm learning Latin American Spanish, Mexican specifically, so keep that in mind when trying to translate the terms to images.

The word is: {word}
"""


async def generate_image(*, client: AsyncOpenAI, word: str, path: str) -> str:
    logger.debug("Generating image", word=word)
    response = await client.images.generate(
        model="dall-e-3",
        prompt=PROMPT_TEMPLATE.format(word=word),
        n=1,
        size="1024x1024",
        response_format="b64_json",
    )
    logger.debug("Received image response", word=word)

    if response.data:
        image_data = base64.b64decode(response.data[0].b64_json or "")

        logger.info("Writing file", word=word, path=path)
        with open(file=path, mode="wb") as f:
            f.write(image_data)
        return path
    else:
        raise RuntimeError("No image data received from API")


def view_image(path: str):
    image = from_file(path)
    image.draw()
