import base64

from loguru import logger
from openai import AsyncOpenAI
from term_image.image import from_file


async def generate_image(*, client: AsyncOpenAI, word: str, path: str) -> str:
    logger.debug("Generating image", word=word)
    response = await client.images.generate(
        model="dall-e-3",
        prompt=f"Create a clear, educational image representing the Spanish word '{word}'. The image should help language learners remember the meaning.",
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
