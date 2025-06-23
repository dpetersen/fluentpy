import questionary
from loguru import logger

from models import WordInput, ClozeCardInput


async def get_vocabulary_word_inputs() -> list[WordInput]:
    """Interactively collect words and metadata for vocabulary cards."""
    word_inputs: list[WordInput] = []

    logger.info("Starting vocabulary word input collection")
    print("\n📚 Vocabulary Card Collection")
    print("Collect words for traditional vocabulary cards with images and single-word audio.")
    print()

    while True:
        word = await questionary.text(
            "Enter a Spanish word for vocabulary card (or press Enter to finish):",
            validate=lambda text: True if text.strip() or not text else False,
        ).ask_async()

        if not word:
            break

        word = word.strip().lower()

        # Always ask for personal context (optional - can be empty)
        personal_context_input = await questionary.text(
            "Personal context (memory aid, usage example, etc.) - press Enter to skip:"
        ).ask_async()
        personal_context = (
            personal_context_input.strip() if personal_context_input.strip() else None
        )

        # Always ask for extra image prompt (optional - can be empty)
        extra_image_prompt_input = await questionary.text(
            "Extra image prompt (additional context for image generation) - press Enter to skip:"
        ).ask_async()
        extra_image_prompt = (
            extra_image_prompt_input.strip()
            if extra_image_prompt_input.strip()
            else None
        )

        word_input = WordInput(
            word=word,
            personal_context=personal_context,
            extra_image_prompt=extra_image_prompt,
        )
        word_inputs.append(word_input)

        logger.info(
            "Vocabulary word added",
            word=word,
            has_context=bool(personal_context),
            has_image_prompt=bool(extra_image_prompt),
        )

    logger.info("Vocabulary word collection complete", count=len(word_inputs))
    return word_inputs


async def get_cloze_word_inputs() -> list[ClozeCardInput]:
    """Interactively collect words and metadata for Cloze cards."""
    word_inputs: list[ClozeCardInput] = []

    logger.info("Starting Cloze word input collection")
    print("\n🧩 Cloze Card Collection")
    print("Collect words for Cloze cards with sentence context and full sentence audio.")
    print()

    while True:
        word = await questionary.text(
            "Enter a Spanish word for Cloze card (or press Enter to finish):",
            validate=lambda text: True if text.strip() or not text else False,
        ).ask_async()

        if not word:
            break

        word = word.strip().lower()

        # Ask for optional definitions
        definitions_input = await questionary.text(
            "Definitions/base word info (for front of card) - press Enter to skip:"
        ).ask_async()
        definitions = (
            definitions_input.strip() if definitions_input.strip() else None
        )

        # Always ask for personal context (optional - can be empty)
        personal_context_input = await questionary.text(
            "Personal context (memory aid, usage example, etc.) - press Enter to skip:"
        ).ask_async()
        personal_context = (
            personal_context_input.strip() if personal_context_input.strip() else None
        )

        # Always ask for extra image prompt (optional - can be empty)
        extra_image_prompt_input = await questionary.text(
            "Extra image prompt (additional context for image generation) - press Enter to skip:"
        ).ask_async()
        extra_image_prompt = (
            extra_image_prompt_input.strip()
            if extra_image_prompt_input.strip()
            else None
        )

        word_input = ClozeCardInput(
            word=word,
            definitions=definitions,
            personal_context=personal_context,
            extra_image_prompt=extra_image_prompt,
        )
        word_inputs.append(word_input)

        logger.info(
            "Cloze word added",
            word=word,
            has_definitions=bool(definitions),
            has_context=bool(personal_context),
            has_image_prompt=bool(extra_image_prompt),
        )

    logger.info("Cloze word collection complete", count=len(word_inputs))
    return word_inputs


async def get_all_word_inputs() -> tuple[list[WordInput], list[ClozeCardInput]]:
    """Collect both vocabulary and Cloze word inputs in sequence."""
    # First collect vocabulary words
    vocabulary_inputs = await get_vocabulary_word_inputs()
    
    # Then collect Cloze words
    cloze_inputs = await get_cloze_word_inputs()
    
    return vocabulary_inputs, cloze_inputs


def get_words_from_list(words: list[str]) -> list[WordInput]:
    """Convert a list of words to WordInput objects without metadata."""
    return [WordInput(word=word.strip().lower()) for word in words if word.strip()]


def get_cloze_words_from_list(words: list[str]) -> list[ClozeCardInput]:
    """Convert a list of words to ClozeCardInput objects without metadata."""
    return [ClozeCardInput(word=word.strip().lower()) for word in words if word.strip()]
