import random
from typing import Optional

from elevenlabs.client import AsyncElevenLabs
from elevenlabs.types import Voice
from loguru import logger


async def get_mexican_spanish_voices(client: AsyncElevenLabs) -> list[Voice]:
    """Get list of voices suitable for Mexican Spanish pronunciation using server-side search."""
    try:
        # Search for Mexican Spanish voices
        logger.info("Searching for Mexican Spanish voices")
        try:
            response = await client.voices.search(search="Spanish (Es-mexican)")

            if response.voices:
                logger.info("Found Mexican Spanish voices", count=len(response.voices))
                return response.voices

        except Exception as search_error:
            logger.warning("Mexican Spanish search failed", error=str(search_error))

        # If targeted search fails, try a general search as fallback
        logger.warning("No Mexican Spanish voices found, trying general search")
        try:
            response = await client.voices.search()
            if response.voices:
                logger.info(
                    "Using general voices as fallback", count=len(response.voices)
                )
                return response.voices[:10]  # Limit to first 10 for performance
        except Exception as fallback_error:
            logger.error("Even fallback search failed", error=str(fallback_error))

        logger.error("No voices found with any search strategy")
        return []

    except Exception as e:
        logger.error("Error in voice search", error=str(e))
        return []


async def generate_audio(
    client: AsyncElevenLabs, word: str, path: str
) -> Optional[str]:
    """Generate audio pronunciation for a Spanish word and save to file."""
    try:
        # Get available Mexican Spanish voices
        voices = await get_mexican_spanish_voices(client)

        if not voices:
            logger.error(
                "No Mexican Spanish voices found - check ElevenLabs voice library"
            )
            return None

        # Randomly select a voice
        selected_voice = random.choice(voices)
        logger.info(
            "Selected voice for audio generation",
            voice_name=selected_voice.name,
            voice_id=selected_voice.voice_id,
        )

        # Generate audio using multilingual model
        audio_generator = client.text_to_speech.convert(
            text=word,
            voice_id=selected_voice.voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        # Save audio to file
        with open(path, "wb") as f:
            async for chunk in audio_generator:
                f.write(chunk)

        logger.info("Audio saved successfully", path=path)
        return path

    except Exception as e:
        logger.error("Error generating audio", word=word, error=str(e))
        return None
