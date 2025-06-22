import random
from typing import Optional

from elevenlabs.client import AsyncElevenLabs
from elevenlabs.types import LibraryVoiceResponse
from loguru import logger


async def get_mexican_spanish_voices(
    client: AsyncElevenLabs,
) -> list[LibraryVoiceResponse]:
    """Get list of voices suitable for Mexican Spanish pronunciation using server-side search."""
    try:
        # Search for Mexican Spanish voices
        logger.info("Searching for Mexican Spanish voices")
        try:
            response = await client.voices.get_shared(search="spanish")

            if response.voices:
                # Filter for voices available on starter/free tier
                starter_voices = []
                for voice in response.voices:
                    # Log voice attributes to understand tier requirements
                    logger.debug(
                        "Voice attributes",
                        name=voice.name,
                        voice_id=voice.voice_id,
                        category=getattr(voice, "category", None),
                        use_case=getattr(voice, "use_case", None),
                    )
                    # For now, include all voices and let the API tell us which ones work
                    starter_voices.append(voice)

                if starter_voices:
                    logger.info(
                        "Found starter-tier Spanish voices", count=len(starter_voices)
                    )
                    return starter_voices
                else:
                    logger.warning(
                        "Found voices but none available for starter tier",
                        total_count=len(response.voices),
                    )

        except Exception as search_error:
            logger.warning("Shared Spanish search failed", error=str(search_error))

        # If targeted search fails, try a general shared voices search as fallback
        logger.warning("No Spanish shared voices found, trying general shared search")
        try:
            response = await client.voices.get_shared()
            if response.voices:
                # Filter for starter tier voices
                starter_voices = []
                for voice in response.voices[:10]:  # Limit to 10 for performance
                    # For now, include all voices since we can't determine tier requirements
                    starter_voices.append(voice)

                if starter_voices:
                    logger.info(
                        "Using general shared starter-tier voices as fallback",
                        count=len(starter_voices),
                    )
                    return starter_voices
                else:
                    logger.warning("No starter-tier voices found in fallback")
        except Exception as fallback_error:
            logger.error(
                "Even fallback shared search failed", error=str(fallback_error)
            )

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

        # Try voices until we find one that works for our tier
        voices_to_try = list(voices)  # Make a copy to shuffle
        random.shuffle(voices_to_try)  # Randomize order

        for selected_voice in voices_to_try:
            try:
                logger.info(
                    "Trying voice for audio generation",
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

                logger.info(
                    "Audio saved successfully",
                    path=path,
                    voice_used=selected_voice.name,
                )
                return path

            except Exception as voice_error:
                error_str = str(voice_error)
                if (
                    "free_users_not_allowed" in error_str
                    or "creator tier" in error_str.lower()
                ):
                    logger.warning(
                        "Voice requires higher tier, trying next",
                        voice_name=selected_voice.name,
                        error=error_str,
                    )
                    continue
                else:
                    # Re-raise non-tier-related errors
                    raise

        logger.error("No voices worked for current tier", word=word)
        return None

    except Exception as e:
        logger.error("Error generating audio", word=word, error=str(e))
        return None
