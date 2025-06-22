import random
from typing import Optional

from elevenlabs.client import AsyncElevenLabs
from loguru import logger

# Hardcoded Mexican Spanish voice IDs to avoid quota limits
MEXICAN_SPANISH_VOICES = [
    "CaJslL1xziwefCeTNzHv",  # Cristina Campos, conversational
    "gbTn1bmCvNgk0QEAVyfM",  # Enrique Nieto, Educational
    "qXvyMc4erc4RzqXLpiiR",  # Aljandro, Narrative
]


def get_random_voice_id() -> str:
    """Get a random Mexican Spanish voice ID from the hardcoded list."""
    return random.choice(MEXICAN_SPANISH_VOICES)


async def generate_audio(
    client: AsyncElevenLabs, word: str, path: str
) -> Optional[str]:
    """Generate audio pronunciation for a Spanish word and save to file."""
    try:
        # Get a random voice ID from our hardcoded list
        voice_id = get_random_voice_id()

        logger.info(
            "Using hardcoded voice for audio generation",
            voice_id=voice_id,
            model="eleven_flash_v2_5",
            language_code="es",
        )

        # Generate audio using Flash v2.5 model with Spanish
        audio_generator = client.text_to_speech.convert(
            text=word,
            voice_id=voice_id,
            model_id="eleven_flash_v2_5",
            language_code="es",
            output_format="mp3_44100_128",
        )

        # Save audio to file
        with open(path, "wb") as f:
            async for chunk in audio_generator:
                f.write(chunk)

        logger.info(
            "Audio saved successfully",
            path=path,
            voice_id=voice_id,
        )
        return path

    except Exception as e:
        logger.error("Error generating audio", word=word, error=str(e))
        return None
