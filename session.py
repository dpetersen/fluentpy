import asyncio
from pathlib import Path

from elevenlabs.client import AsyncElevenLabs
from loguru import logger
from openai import AsyncOpenAI

from audio import generate_audio
from images import generate_image
from models import Session, WordCard, WordInput, ClozeCard, ClozeCardInput
from typing import Union
from word_analysis import WordAnalysis, analyze_word

# Limit concurrent API operations to avoid rate limiting
MAX_CONCURRENT_OPERATIONS = 2


async def create_session(
    vocabulary_inputs: list[WordInput] | None = None,
    cloze_inputs: list[ClozeCardInput] | None = None,
    output_directory: Path | None = None,
    words_with_mnemonic: set[str] | None = None,
) -> Session:
    """Create a session from vocabulary and/or Cloze word inputs."""
    if output_directory is None:
        output_directory = Path("./output")

    output_directory.mkdir(parents=True, exist_ok=True)
    session = Session(output_directory=output_directory)

    vocabulary_inputs = vocabulary_inputs or []
    cloze_inputs = cloze_inputs or []
    words_with_mnemonic = words_with_mnemonic or set()
    total_words = len(vocabulary_inputs) + len(cloze_inputs)

    logger.info(
        "Creating session",
        vocabulary_count=len(vocabulary_inputs),
        cloze_count=len(cloze_inputs),
        total_words=total_words,
    )

    if total_words == 0:
        logger.warning("No words provided to create session")
        return session

    # Create OpenAI client for word analysis
    openai_client = AsyncOpenAI()

    # Use semaphore to limit concurrent word analysis across ALL requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)

    async def analyze_word_with_limit(word: str, request_examples: bool):
        async with semaphore:
            return await analyze_word(
                client=openai_client, word=word, request_examples=request_examples
            )

    # Create analysis tasks for all words (respecting concurrency limit)
    analysis_tasks = []
    all_inputs = []

    # Add vocabulary word tasks
    for word_input in vocabulary_inputs:
        analysis_tasks.append(
            analyze_word_with_limit(word_input.word, request_examples=False)
        )
        all_inputs.append((word_input, "vocabulary"))

    # Add cloze word tasks
    for word_input in cloze_inputs:
        analysis_tasks.append(
            analyze_word_with_limit(word_input.word, request_examples=True)
        )
        all_inputs.append((word_input, "cloze"))

    # Run all analyses with proper concurrency control
    analyses = await asyncio.gather(*analysis_tasks)

    # Create cards from inputs and analyses
    for (word_input, card_type), analysis in zip(all_inputs, analyses):
        if card_type == "vocabulary":
            card = WordCard(
                word=word_input.word,
                ipa=analysis["ipa"],
                part_of_speech=analysis["part_of_speech"],
                gender=analysis.get("gender"),
                verb_type=analysis.get("verb_type"),
                personal_context=word_input.personal_context,
                extra_image_prompt=word_input.extra_image_prompt,
                has_mnemonic_image=(word_input.word in words_with_mnemonic),
            )
            session.add_card(card)

            logger.info(
                "Vocabulary word analyzed and added to session",
                word=card.word,
                ipa=card.ipa,
                part_of_speech=card.part_of_speech,
            )
        else:  # cloze
            card = ClozeCard(
                word=word_input.word,
                word_analysis=analysis,
                personal_context=word_input.personal_context,
                extra_prompt=word_input.extra_image_prompt,
                memory_aid=word_input.definitions,
                has_mnemonic_image=(word_input.word in words_with_mnemonic),
            )
            session.add_card(card)

            logger.info(
                "Cloze word analyzed and added to session",
                word=card.word,
                ipa=card.ipa,
                part_of_speech=card.part_of_speech,
                example_count=len(card.example_sentences),
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

    async def generate_media_for_card(card: Union[WordCard, ClozeCard]):
        async with semaphore:
            logger.info("Generating media", word=card.word, card_type=card.card_type)

            # Generate paths for media files
            image_path = session.get_media_path(card, ".jpg")
            audio_path = session.get_media_path(card, ".mp3")

            # Create enhanced analysis for image generation
            enhanced_analysis: WordAnalysis = {
                "ipa": card.ipa,
                "part_of_speech": card.part_of_speech,
                "gender": card.gender,
                "verb_type": card.verb_type,
                "example_sentences": [],
            }

            # For Cloze cards, check if sentence is selected for context-based generation
            if isinstance(card, ClozeCard) and card.selected_sentence:
                # Use sentence-based generation
                image_task = generate_image(
                    client=openai_client,
                    word=card.word,
                    analysis=enhanced_analysis,
                    path=str(image_path),
                    extra_prompt=card.extra_image_prompt,
                    sentence_context=card.selected_sentence,
                )

                audio_task = generate_audio(
                    client=elevenlabs_client,
                    text=card.selected_sentence,  # Full sentence for Cloze cards
                    path=str(audio_path),
                )
            else:
                # Standard word-based generation (vocabulary cards or Cloze without sentence)
                image_task = generate_image(
                    client=openai_client,
                    word=card.word,
                    analysis=enhanced_analysis,
                    path=str(image_path),
                    extra_prompt=card.extra_image_prompt,
                )

                audio_task = generate_audio(
                    client=elevenlabs_client,
                    text=card.word,  # Single word for vocabulary cards
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
    session: Session,
    card: Union[WordCard, ClozeCard],
    additional_prompt: str | None = None,
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
        "example_sentences": [],
    }

    # Combine original extra prompt with additional regeneration context
    combined_extra_prompt = card.extra_image_prompt
    if additional_prompt:
        if combined_extra_prompt:
            combined_extra_prompt = f"{combined_extra_prompt}. {additional_prompt}"
        else:
            combined_extra_prompt = additional_prompt

    try:
        # For Cloze cards with selected sentence, use sentence context
        if isinstance(card, ClozeCard) and card.selected_sentence:
            result_path = await generate_image(
                client=openai_client,
                word=card.word,
                analysis=enhanced_analysis,
                path=str(image_path),
                extra_prompt=combined_extra_prompt,
                sentence_context=card.selected_sentence,
            )
        else:
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


async def regenerate_audio(session: Session, card: Union[WordCard, ClozeCard]) -> bool:
    """Regenerate audio for a specific card with a different voice."""
    logger.info("Regenerating audio", word=card.word)

    elevenlabs_client = AsyncElevenLabs()

    # Use the same path (regeneration replaces the old audio)
    audio_path = session.get_media_path(card, ".mp3")

    try:
        # For Cloze cards with selected sentence, use full sentence
        if isinstance(card, ClozeCard) and card.selected_sentence:
            result_path = await generate_audio(
                client=elevenlabs_client,
                text=card.selected_sentence,
                path=str(audio_path),
            )
        else:
            result_path = await generate_audio(
                client=elevenlabs_client,
                text=card.word,
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
