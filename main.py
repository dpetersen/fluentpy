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

    analysis_task = analyze_word(client=openai_client, word=word)
    image_task = None
    audio_task = None

    if should_generate_image:
        logger.info("Generating image", word=word)
        try:
            image_path = f"./{word}.png"
            image_task = generate_image(
                client=openai_client, word=word, path=image_path
            )
        except Exception as e:
            logger.error("Error generating image", word=word, error=str(e))

    if should_generate_audio:
        logger.info("Generating audio", word=word)
        try:
            audio_path = f"./{word}.mp3"
            audio_task = generate_audio(
                client=elevenlabs_client, word=word, path=audio_path
            )
        except Exception as e:
            logger.error("Error generating audio", word=word, error=str(e))

    tasks: list = [analysis_task]
    if image_task is not None:
        tasks.append(image_task)
    if audio_task is not None:
        tasks.append(audio_task)

    results = await asyncio.gather(*tasks)
    analysis = results[0]
    logger.info(
        "Word analysis complete",
        word=word,
        ipa=analysis["ipa"],
        part_of_speech=analysis["part_of_speech"],
        gender=analysis["gender"],
        verb_type=analysis["verb_type"],
    )

    result_index = 1
    if should_generate_image and len(results) > result_index:
        image_path = results[result_index]
        if image_path:
            logger.info("Image saved", path=image_path)
            view_image(path=image_path)
        result_index += 1

    if should_generate_audio and len(results) > result_index:
        audio_path = results[result_index]
        if audio_path:
            logger.info("Audio saved", path=audio_path)


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
