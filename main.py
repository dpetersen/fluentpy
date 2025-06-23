import asyncio
import subprocess
import sys

import questionary
from loguru import logger

from anki_export import export_to_anki
from cloze_export import export_cloze_cards_to_anki
from config import AnkiConfig, ClozeAnkiConfig
from review import review_session, show_session_summary, select_sentence_for_cloze_card
from session import create_session, generate_media_for_session
from word_input import get_all_word_inputs

# Configure loguru to show extra fields
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> <dim>{extra}</dim>",
    level="INFO",
)


def check_mpv_availability() -> bool:
    """Check if mpv is available in PATH."""
    try:
        result = subprocess.run(
            ["mpv", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


async def main():
    """Complete FluentPy workflow: input → generation → review → export."""
    # Check for required dependencies first
    if not check_mpv_availability():
        print("❌ Error: mpv is required for audio playback but not found.")
        print("Please install mpv:")
        print("  • macOS: brew install mpv")
        print("  • Ubuntu/Debian: sudo apt install mpv")
        print("  • Arch Linux: sudo pacman -S mpv")
        print("  • Or visit: https://mpv.io/installation/")
        sys.exit(1)
    
    logger.info("Starting FluentPy session")

    # Step 1: Collect words from user (two-phase: vocabulary + Cloze)
    print("🇪🇸 FluentPy - Spanish Flashcard Generator")
    print("=" * 60)
    print("Create Anki flashcards with images and audio.")
    print("• Vocabulary cards: Traditional word-based cards")
    print("• Cloze cards: Sentence-based cards with word blanked out")
    print()

    vocabulary_inputs, cloze_inputs = await get_all_word_inputs()
    total_words = len(vocabulary_inputs) + len(cloze_inputs)

    if total_words == 0:
        print("No words entered. Exiting.")
        return

    print(f"\n📝 Processing {total_words} words...")
    print(f"   📚 Vocabulary cards: {len(vocabulary_inputs)}")
    print(f"   🧩 Cloze cards: {len(cloze_inputs)}")

    # Step 2: Create session and analyze words
    try:
        session = await create_session(
            vocabulary_inputs=vocabulary_inputs,
            cloze_inputs=cloze_inputs
        )
        logger.info("Session created", total_cards=len(session.cards))
    except Exception as e:
        logger.error("Failed to create session", error=str(e))
        print(f"❌ Error analyzing words: {e}")
        return

    # Step 2.5: Select sentences for Cloze cards before media generation
    cloze_cards = session.cloze_cards
    if cloze_cards:
        print(f"\n🧩 Selecting sentences for {len(cloze_cards)} Cloze cards...")
        print("Choose one sentence for each word to create fill-in-the-blank cards:")
        print()
        
        try:
            for card in cloze_cards:
                await select_sentence_for_cloze_card(card)
            logger.info("Sentence selection completed for all Cloze cards")
        except Exception as e:
            logger.error("Failed during sentence selection", error=str(e))
            print(f"❌ Error selecting sentences: {e}")
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
    vocabulary_cards = session.vocabulary_cards
    cloze_cards = session.cloze_cards
    
    if vocabulary_cards or cloze_cards:
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

            export_results = []
            
            # Export vocabulary cards if any exist
            if vocabulary_cards:
                print(f"\n📚 Exporting {len(vocabulary_cards)} vocabulary cards...")
                vocab_config = AnkiConfig(deck_name=deck_name)
                try:
                    vocab_success = export_to_anki(session, vocab_config)
                    export_results.append(("vocabulary", vocab_success))
                    if vocab_success:
                        logger.info("Vocabulary export completed successfully")
                    else:
                        logger.error("Vocabulary export failed")
                        print("❌ Vocabulary export failed. Check the logs for details.")
                except Exception as e:
                    logger.error("Vocabulary export error", error=str(e))
                    print(f"❌ Vocabulary export error: {e}")
                    export_results.append(("vocabulary", False))

            # Export Cloze cards if any exist
            if cloze_cards:
                print(f"\n🧩 Exporting {len(cloze_cards)} Cloze cards...")
                cloze_config = ClozeAnkiConfig(deck_name=deck_name)
                try:
                    cloze_success = export_cloze_cards_to_anki(session, cloze_config)
                    export_results.append(("cloze", cloze_success))
                    if cloze_success:
                        logger.info("Cloze export completed successfully")
                    else:
                        logger.error("Cloze export failed")
                        print("❌ Cloze export failed. Check the logs for details.")
                except Exception as e:
                    logger.error("Cloze export error", error=str(e))
                    print(f"❌ Cloze export error: {e}")
                    export_results.append(("cloze", False))

            # Summary of export results
            successful_exports = [card_type for card_type, success in export_results if success]
            failed_exports = [card_type for card_type, success in export_results if not success]
            
            if successful_exports:
                print(f"\n✅ Successfully exported: {', '.join(successful_exports)}")
            if failed_exports:
                print(f"\n❌ Failed to export: {', '.join(failed_exports)}")
                
        else:
            print("\n💾 Session saved. You can export later.")
    else:
        print("\n⚠️  No cards to export.")

    print("\n🎉 FluentPy session complete!")
    if vocabulary_cards and cloze_cards:
        print(f"   📚 Vocabulary cards: {len(vocabulary_cards)}")
        print(f"   🧩 Cloze cards: {len(cloze_cards)}")
        print("\n📝 Import Instructions:")
        print("   • Two separate CSV files were created")
        print("   • Import each CSV file separately in Anki")
        print("   • Media files are shared between both card types")


if __name__ == "__main__":
    asyncio.run(main())
