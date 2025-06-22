import asyncio
import sys

import questionary
from elevenlabs.client import AsyncElevenLabs
from loguru import logger
from openai import AsyncOpenAI

from audio import generate_audio
from images import generate_image, view_image
from word_analysis import analyze_word

# Configure loguru to show extra fields
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> <dim>{extra}</dim>",
    level="DEBUG",
)


async def process_word(
    word: str, should_generate_image: bool, should_generate_audio: bool
):
    # Will automatically use OPENAI_API_KEY and ELEVENLABS_API_KEY environment variables
    openai_client = AsyncOpenAI()
    elevenlabs_client = AsyncElevenLabs()

    analysis = await analyze_word(client=openai_client, word=word)
    logger.info(
        "Word analysis complete",
        word=word,
        ipa=analysis["ipa"],
        part_of_speech=analysis["part_of_speech"],
        gender=analysis["gender"],
        verb_type=analysis["verb_type"],
    )

    tasks: list = []
    if should_generate_image:
        logger.info("Generating image", word=word)
        try:
            image_path = f"./{word}.jpg"
            image_task = generate_image(
                client=openai_client, word=word, analysis=analysis, path=image_path
            )
            tasks.append(("image", image_task))
        except Exception as e:
            logger.error("Error generating image", word=word, error=str(e))

    if should_generate_audio:
        logger.info("Generating audio", word=word)
        try:
            audio_path = f"./{word}.mp3"
            audio_task = generate_audio(
                client=elevenlabs_client, word=word, path=audio_path
            )
            tasks.append(("audio", audio_task))
        except Exception as e:
            logger.error("Error generating audio", word=word, error=str(e))

    if tasks:
        task_results = await asyncio.gather(*[task for _, task in tasks])

        for i, (task_type, _) in enumerate(tasks):
            result = task_results[i]
            if task_type == "image" and result:
                logger.info("Image saved", path=result)
                view_image(path=result)
            elif task_type == "audio" and result:
                logger.info("Audio saved", path=result)


def main():
    word = questionary.text(message="What is the word?").ask()
    should_generate_image = questionary.confirm(
        message=f"Would you like to generate an image for '{word}'?", default=True
    ).ask()
    should_generate_audio = questionary.confirm(
        message=f"Would you like to generate audio for '{word}'?", default=True
    ).ask()

    asyncio.run(
        process_word(
            word=word,
            should_generate_image=should_generate_image,
            should_generate_audio=should_generate_audio,
        )
    )


if __name__ == "__main__":
    main()
