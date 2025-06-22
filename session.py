import asyncio
from pathlib import Path

from elevenlabs.client import AsyncElevenLabs
from loguru import logger
from openai import AsyncOpenAI

from audio import generate_audio
from images import generate_image
from models import Session, WordCard, WordInput
from word_analysis import WordAnalysis, analyze_word

# Limit concurrent API operations to avoid rate limiting
MAX_CONCURRENT_OPERATIONS = 2


async def create_session(
    word_inputs: list[WordInput], output_directory: Path | None = None
) -> Session:
    """Create a session from word inputs and analyze each word."""
    if output_directory is None:
        output_directory = Path("./output")

    output_directory.mkdir(parents=True, exist_ok=True)
    session = Session(output_directory=output_directory)

    logger.info("Creating session", word_count=len(word_inputs))

    # Create OpenAI client for word analysis
    openai_client = AsyncOpenAI()

    # Use semaphore to limit concurrent word analysis
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)

    async def analyze_with_limit(word_input: WordInput):
        async with semaphore:
            return await analyze_word(client=openai_client, word=word_input.word)

    # Analyze words with concurrency limit
    analysis_tasks = [analyze_with_limit(word_input) for word_input in word_inputs]
    analyses = await asyncio.gather(*analysis_tasks)

    # Create WordCards from inputs and analyses
    for word_input, analysis in zip(word_inputs, analyses):
        card = WordCard(
            word=word_input.word,
            ipa=analysis["ipa"],
            part_of_speech=analysis["part_of_speech"],
            gender=analysis.get("gender"),
            verb_type=analysis.get("verb_type"),
            personal_context=word_input.personal_context,
            extra_image_prompt=word_input.extra_image_prompt,
        )
        session.add_card(card)

        logger.info(
            "Word analyzed and added to session",
            word=card.word,
            ipa=card.ipa,
            part_of_speech=card.part_of_speech,
        )

    logger.info("Session created successfully", total_cards=len(session.cards))
    return session


async def generate_media_for_session(session: Session) -> None:
    """Generate images and audio for all cards in the session with concurrency limits."""
    logger.info("Starting media generation", card_count=len(session.cards))

    openai_client = AsyncOpenAI()
    elevenlabs_client = AsyncElevenLabs()

    # Use semaphore to limit concurrent media generation
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)

    async def generate_media_for_card(card: WordCard):
        async with semaphore:
            logger.info("Generating media", word=card.word)

            # Generate paths for media files
            image_path = session.get_media_path(card, ".jpg")
            audio_path = session.get_media_path(card, ".mp3")

            # Create enhanced image prompt if extra context provided
            enhanced_analysis: WordAnalysis = {
                "ipa": card.ipa,
                "part_of_speech": card.part_of_speech,
                "gender": card.gender,
                "verb_type": card.verb_type,
            }

            # Generate image and audio concurrently for this card
            image_task = generate_image(
                client=openai_client,
                word=card.word,
                analysis=enhanced_analysis,
                path=str(image_path),
                extra_prompt=card.extra_image_prompt,
            )

            audio_task = generate_audio(
                client=elevenlabs_client,
                word=card.word,
                path=str(audio_path),
            )

            try:
                results = await asyncio.gather(
                    image_task, audio_task, return_exceptions=True
                )

                # Handle image generation result
                if not isinstance(results[0], Exception):
                    card.image_path = image_path
                    logger.info("Image generated", word=card.word, path=image_path)
                else:
                    logger.error(
                        "Image generation failed", word=card.word, error=str(results[0])
                    )

                # Handle audio generation result
                if not isinstance(results[1], Exception):
                    card.audio_path = audio_path
                    logger.info("Audio generated", word=card.word, path=audio_path)
                else:
                    logger.error(
                        "Audio generation failed", word=card.word, error=str(results[1])
                    )

            except Exception as e:
                logger.error("Media generation failed", word=card.word, error=str(e))

    # Process all cards with concurrency limit
    media_tasks = [generate_media_for_card(card) for card in session.cards]
    await asyncio.gather(*media_tasks)

    logger.info("Media generation completed")


async def regenerate_image(
    session: Session, card: WordCard, additional_prompt: str | None = None
) -> bool:
    """Regenerate image for a specific card, optionally with additional prompt context."""
    logger.info("Regenerating image", word=card.word)

    openai_client = AsyncOpenAI()

    # Use the same path (regeneration replaces the old image)
    image_path = session.get_media_path(card, ".jpg")

    # Build enhanced analysis with additional context
    enhanced_analysis: WordAnalysis = {
        "ipa": card.ipa,
        "part_of_speech": card.part_of_speech,
        "gender": card.gender,
        "verb_type": card.verb_type,
    }

    # Combine original extra prompt with additional regeneration context
    combined_extra_prompt = card.extra_image_prompt
    if additional_prompt:
        if combined_extra_prompt:
            combined_extra_prompt = f"{combined_extra_prompt}. {additional_prompt}"
        else:
            combined_extra_prompt = additional_prompt

    try:
        result_path = await generate_image(
            client=openai_client,
            word=card.word,
            analysis=enhanced_analysis,
            path=str(image_path),
            extra_prompt=combined_extra_prompt,
        )

        if result_path:
            card.image_path = image_path
            logger.info(
                "Image regenerated successfully", word=card.word, path=image_path
            )
            return True

    except Exception as e:
        logger.error("Image regeneration failed", word=card.word, error=str(e))

    return False


async def regenerate_audio(session: Session, card: WordCard) -> bool:
    """Regenerate audio for a specific card with a different voice."""
    logger.info("Regenerating audio", word=card.word)

    elevenlabs_client = AsyncElevenLabs()

    # Use the same path (regeneration replaces the old audio)
    audio_path = session.get_media_path(card, ".mp3")

    try:
        result_path = await generate_audio(
            client=elevenlabs_client,
            word=card.word,
            path=str(audio_path),
        )

        if result_path:
            card.audio_path = Path(result_path)
            logger.info(
                "Audio regenerated successfully", word=card.word, path=audio_path
            )
            return True

    except Exception as e:
        logger.error("Audio regeneration failed", word=card.word, error=str(e))

    return False
