import subprocess
from pathlib import Path

import questionary
from loguru import logger

from images import view_image
from models import Session, WordCard
from session import regenerate_audio, regenerate_image


async def review_session(session: Session) -> None:
    """Interactive review of all cards in the session until all are approved."""
    logger.info("Starting session review", total_cards=len(session.cards))

    while not session.is_complete:
        incomplete_cards = session.incomplete_cards

        # Show progress
        completed_count = len(session.cards) - len(incomplete_cards)
        logger.info(
            "Review progress",
            completed=completed_count,
            remaining=len(incomplete_cards),
            total=len(session.cards),
        )

        # Let user choose which card to review
        card_choices = [
            f"{card.word} - {card.ipa} ({card.part_of_speech})"
            for card in incomplete_cards
        ]

        if len(card_choices) == 1:
            # Only one card left, review it automatically
            selected_card = incomplete_cards[0]
        else:
            choice = await questionary.select(
                "Select a word to review:", choices=card_choices
            ).ask_async()

            # Find the selected card
            selected_index = card_choices.index(choice)
            selected_card = incomplete_cards[selected_index]

        # Review the selected card
        await review_card(session, selected_card)

    logger.info("All cards approved! Session review complete.")


async def review_card(session: Session, card: WordCard) -> None:
    """Review a single card and allow user to approve or regenerate media."""
    logger.info("Reviewing card", word=card.word)

    # Display card information
    print(f"\n{'=' * 50}")
    print(f"Word: {card.word}")
    print(f"IPA: {card.ipa}")
    print(f"Part of speech: {card.part_of_speech}")
    if card.gender:
        print(f"Gender: {card.gender}")
    if card.verb_type:
        print(f"Verb type: {card.verb_type}")
    if card.personal_context:
        print(f"Personal context: {card.personal_context}")
    if card.extra_image_prompt:
        print(f"Extra image prompt: {card.extra_image_prompt}")
    print(f"{'=' * 50}")

    # Display generated media
    await display_card_media(card)

    # Review loop for this card
    while True:
        actions = ["✅ Approve this card"]

        if card.image_path:
            actions.append("🖼️  Regenerate image")

        if card.audio_path:
            actions.append("🔊 Regenerate audio")
            actions.append("🔈 Replay audio")

        action = await questionary.select(
            f"What would you like to do with '{card.word}'?",
            choices=actions,
        ).ask_async()

        if action.startswith("✅"):
            card.mark_complete()
            logger.info("Card approved", word=card.word)
            break
        elif action.startswith("🖼️"):
            await handle_image_regeneration(session, card)
        elif action.startswith("🔊"):
            await handle_audio_regeneration(session, card)
        elif action.startswith("🔈"):
            await handle_audio_replay(card)


async def display_card_media(card: WordCard) -> None:
    """Display the generated media for a card."""
    if card.image_path and card.image_path.exists():
        try:
            print(f"\nDisplaying image: {card.image_path}")
            view_image(str(card.image_path))
        except Exception as e:
            logger.error("Failed to display image", word=card.word, error=str(e))
            print(f"❌ Could not display image: {e}")
    else:
        print("❌ No image available")

    if card.audio_path and card.audio_path.exists():
        print(f"🔊 Playing audio: {card.audio_path}")
        play_audio(card.audio_path)
    else:
        print("❌ No audio available")


async def handle_image_regeneration(session: Session, card: WordCard) -> None:
    """Handle user request to regenerate image with optional additional context."""
    print(f"\nRegenerating image for '{card.word}'...")

    # Ask for additional context
    additional_context = await questionary.text(
        "Additional image context (press Enter to skip):",
        instruction="e.g., 'make it more colorful', 'add a dog', 'sunset lighting'",
    ).ask_async()

    additional_prompt = (
        additional_context.strip() if additional_context.strip() else None
    )

    logger.info(
        "Starting image regeneration",
        word=card.word,
        has_additional_context=bool(additional_prompt),
    )

    success = await regenerate_image(session, card, additional_prompt)

    if success:
        print("✅ Image regenerated successfully!")
        # Display the new image
        await display_card_media(card)
    else:
        print("❌ Image regeneration failed. Please try again.")


async def handle_audio_regeneration(session: Session, card: WordCard) -> None:
    """Handle user request to regenerate audio."""
    print(f"\nRegenerating audio for '{card.word}'...")

    logger.info("Starting audio regeneration", word=card.word)

    success = await regenerate_audio(session, card)

    if success:
        print("✅ Audio regenerated successfully!")
        if card.audio_path:
            print(f"🔊 New audio: {card.audio_path}")
            play_audio(card.audio_path)
    else:
        print("❌ Audio regeneration failed. Please try again.")


async def handle_audio_replay(card: WordCard) -> None:
    """Handle user request to replay audio."""
    if card.audio_path and card.audio_path.exists():
        print(f"\n🔈 Replaying audio for '{card.word}'...")
        play_audio(card.audio_path)
    else:
        print("❌ No audio available to replay")


def play_audio(audio_path: Path) -> None:
    """Play audio file using mpv."""
    try:
        # Use mpv with minimal output and no video window
        result = subprocess.run(
            [
                "mpv",
                "--really-quiet",
                "--no-video",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout for audio playback
        )

        if result.returncode == 0:
            logger.info("Audio playback completed", path=audio_path)
        else:
            logger.error(
                "mpv returned non-zero exit code",
                path=audio_path,
                returncode=result.returncode,
                stderr=result.stderr,
            )
            if result.stderr:
                print(f"❌ Audio playback error: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("Audio playback timed out", path=audio_path)
        print("❌ Audio playback timed out")
    except FileNotFoundError:
        logger.error("mpv not found in PATH")
        print("❌ Could not play audio: mpv not found. Please install mpv.")
    except Exception as e:
        logger.error("Failed to play audio", path=audio_path, error=str(e))
        print(f"❌ Could not play audio: {e}")


def show_session_summary(session: Session) -> None:
    """Display a summary of the completed session."""
    print(f"\n{'=' * 60}")
    print("SESSION COMPLETE!")
    print(f"{'=' * 60}")
    print(f"Total cards created: {len(session.cards)}")
    print(f"Output directory: {session.output_directory}")

    print("\nWords processed:")
    for card in session.cards:
        status = "✅" if card.is_complete else "❌"
        media_status = []
        if card.image_path:
            media_status.append("🖼️")
        if card.audio_path:
            media_status.append("🔊")

        print(f"  {status} {card.word} ({card.ipa}) {' '.join(media_status)}")

    print(f"\nAll media files are saved in: {session.output_directory}")
    print("Ready for Anki export!")
    print(f"{'=' * 60}")
