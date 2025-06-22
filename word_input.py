import questionary
from loguru import logger

from models import WordInput


def get_word_inputs() -> list[WordInput]:
    """Interactively collect words and metadata from the user."""
    word_inputs: list[WordInput] = []
    
    logger.info("Starting word input collection")
    
    while True:
        word = questionary.text(
            "Enter a Spanish word (or press Enter to finish):",
            validate=lambda text: True if text.strip() or not text else False,
        ).ask()
        
        if not word:
            break
            
        word = word.strip().lower()
        
        # Always ask for personal context (optional - can be empty)
        personal_context_input = questionary.text(
            "Personal context (memory aid, usage example, etc.) - press Enter to skip:"
        ).ask()
        personal_context = personal_context_input.strip() if personal_context_input.strip() else None
        
        # Always ask for extra image prompt (optional - can be empty)
        extra_image_prompt_input = questionary.text(
            "Extra image prompt (additional context for image generation) - press Enter to skip:"
        ).ask()
        extra_image_prompt = extra_image_prompt_input.strip() if extra_image_prompt_input.strip() else None
        
        word_input = WordInput(
            word=word,
            personal_context=personal_context,
            extra_image_prompt=extra_image_prompt,
        )
        word_inputs.append(word_input)
        
        logger.info(
            "Word added",
            word=word,
            has_context=bool(personal_context),
            has_image_prompt=bool(extra_image_prompt),
        )
    
    logger.info("Word collection complete", count=len(word_inputs))
    return word_inputs


def get_words_from_list(words: list[str]) -> list[WordInput]:
    """Convert a list of words to WordInput objects without metadata."""
    return [WordInput(word=word.strip().lower()) for word in words if word.strip()]