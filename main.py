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
            image_path = f"./{word}.png"
            image_task = generate_image(client=client, word=word, path=image_path)
        except Exception as e:
            logger.error("Error generating image", word=word, error=str(e))

    tasks = [pronunciation_task]
    if image_task is not None:
        tasks.append(image_task)

    results = await asyncio.gather(*tasks)
    pronunciation = results[0]
    logger.info("Found IPA pronunciation", word=word, pronunciation=pronunciation)
    if should_generate_image and len(results) > 1:
        image_path = results[1]
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
