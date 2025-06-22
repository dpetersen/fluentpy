import asyncio
import sys

import questionary
from loguru import logger

from anki_export import export_to_anki
from config import AnkiConfig
from review import review_session, show_session_summary
from session import create_session, generate_media_for_session
from word_input import get_word_inputs

# Configure loguru to show extra fields
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> <dim>{extra}</dim>",
    level="INFO",
)


async def main():
    """Complete FluentPy workflow: input → generation → review → export."""
    logger.info("Starting FluentPy session")
    
    # Step 1: Collect words from user
    print("🇪🇸 FluentPy - Spanish Flashcard Generator")
    print("=" * 50)
    print("Enter Spanish words to create Anki flashcards with images and audio.")
    print()
    
    word_inputs = await get_word_inputs()
    
    if not word_inputs:
        print("No words entered. Exiting.")
        return
    
    print(f"\n📝 Processing {len(word_inputs)} words...")
    
    # Step 2: Create session and analyze words
    try:
        session = await create_session(word_inputs)
        logger.info("Session created", total_cards=len(session.cards))
    except Exception as e:
        logger.error("Failed to create session", error=str(e))
        print(f"❌ Error analyzing words: {e}")
        return
    
    # Step 3: Generate media for all cards
    print("\n🎨 Generating images and audio...")
    try:
        await generate_media_for_session(session)
        logger.info("Media generation completed")
    except Exception as e:
        logger.error("Failed to generate media", error=str(e))
        print(f"❌ Error generating media: {e}")
        return
    
    # Step 4: Review and approve cards
    print("\n👀 Review your flashcards")
    print("For each word, you can approve the generated media or regenerate it.")
    print()
    
    try:
        await review_session(session)
        logger.info("Review session completed")
    except Exception as e:
        logger.error("Failed during review", error=str(e))
        print(f"❌ Error during review: {e}")
        return
    
    # Step 5: Show session summary
    show_session_summary(session)
    
    # Step 6: Export to Anki
    export_choice = await questionary.confirm(
        "Would you like to export to Anki now?", default=True
    ).ask_async()
    
    if export_choice:
        print("\n📤 Exporting to Anki...")
        
        # Optional: Ask for custom deck name
        use_custom_deck = await questionary.confirm(
            "Export to default deck 'FluentPy Test'?", default=True
        ).ask_async()
        
        deck_name = None
        if not use_custom_deck:
            deck_name = await questionary.text(
                "Enter deck name:", default="FluentPy Test"
            ).ask_async()
        
        config = AnkiConfig(deck_name=deck_name)
        
        try:
            success = export_to_anki(session, config)
            if success:
                logger.info("Export completed successfully")
            else:
                logger.error("Export failed")
                print("❌ Export failed. Check the logs for details.")
        except Exception as e:
            logger.error("Export error", error=str(e))
            print(f"❌ Export error: {e}")
    else:
        print("\n💾 Session saved. You can export later.")
    
    print("\n🎉 FluentPy session complete!")


if __name__ == "__main__":
    asyncio.run(main())