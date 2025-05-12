import asyncio

import questionary
from loguru import logger
from openai import AsyncOpenAI

from images import generate_image, view_image
from pronunciation import get_pronunciation


async def process_word(word: str, should_generate_image: bool):
    # Will automatically use OPENAI_API_KEY environment variable
    client = AsyncOpenAI()

    pronunciation_task = get_pronunciation(client=client, word=word)
    image_task = None

    if should_generate_image:
        logger.info("Generating image", word=word)
        try:
            # FIXME: correct the path
            image_path = f"./{word}.png"
            image_task = generate_image(client=client, word=word, path=image_path)
        except Exception as e:
            logger.error("Error generating image", word=word, error=str(e))

    # FIXME: this errors, because None can't stand in for a task like this
    pronunciation, image_path = await asyncio.gather(pronunciation_task, image_task)
    logger.info("Found IPA pronunciation", word=word, pronunciation=pronunciation)
    if image_path:
        logger.info("Image saved", path=image_path)
        view_image(path=image_path)


def main():
    word = questionary.text(message="What is the word?").ask()
    should_generate_image = questionary.confirm(
        message=f"Would you like to generate an image for '{word}'?", default=True
    ).ask()

    asyncio.run(process_word(word=word, should_generate_image=should_generate_image))


if __name__ == "__main__":
    main()
