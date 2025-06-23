import subprocess
from pathlib import Path

import questionary
from loguru import logger

from images import view_image
from models import Session, WordCard, ClozeCard
from typing import Union
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
        card_choices = []
        for card in incomplete_cards:
            card_type_indicator = "🧩" if isinstance(card, ClozeCard) else "📚"
            choice_text = f"{card_type_indicator} {card.word} - {card.ipa} ({card.part_of_speech})"
            card_choices.append(choice_text)

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

        # Handle sentence selection for Cloze cards before review
        if isinstance(selected_card, ClozeCard) and not selected_card.selected_sentence:
            await select_sentence_for_cloze_card(selected_card)

        # Review the selected card
        await review_card(session, selected_card)

    logger.info("All cards approved! Session review complete.")


async def select_sentence_for_cloze_card(card: ClozeCard) -> None:
    """Let user select one sentence from the example sentences for a Cloze card."""
    logger.info(
        "Starting sentence selection",
        word=card.word,
        sentence_count=len(card.example_sentences),
    )

    print(f"\n🧩 Choose a sentence for '{card.word}':")

    # Create sentence choices for questionary
    sentence_choices = []
    for i, sentence_data in enumerate(card.example_sentences, 1):
        sentence_text = sentence_data["sentence"]
        word_form = sentence_data["word_form"]
        sentence_choices.append(f"{i}. {sentence_text} (uses: {word_form})")

    # Let user select a sentence
    choice = await questionary.select(
        "Select a sentence:", choices=sentence_choices
    ).ask_async()

    # Extract the selected sentence (remove the number prefix)
    selected_index = int(choice.split(".", 1)[0]) - 1
    sentence_data = card.example_sentences[selected_index]

    card.selected_sentence = sentence_data["sentence"]
    card.selected_word_form = sentence_data["word_form"]

    logger.info(
        "Sentence selected",
        word=card.word,
        selected_sentence=sentence_data["sentence"],
        word_form=sentence_data["word_form"],
        index=selected_index + 1,
    )

    print(f"✅ Selected: {sentence_data['sentence']}")
    print(f"   Word form used: {sentence_data['word_form']}")
    print()


async def review_card(session: Session, card: Union[WordCard, ClozeCard]) -> None:
    """Review a single card and allow user to approve or regenerate media."""
    logger.info("Reviewing card", word=card.word, card_type=card.card_type)

    # Display card information
    print(f"\n{'=' * 60}")
    card_type_icon = "🧩" if isinstance(card, ClozeCard) else "📚"
    print(f"{card_type_icon} {card.card_type.title()} Card: {card.word}")
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

    # Show Cloze-specific information
    if isinstance(card, ClozeCard):
        if card.definitions:
            print(f"Definitions: {card.definitions}")
        if card.selected_sentence:
            print(f"Selected sentence: {card.selected_sentence}")
        else:
            print("⚠️  No sentence selected yet")

    print(f"{'=' * 60}")

    # Display generated media
    await display_card_media(card)

    # Review loop for this card
    while True:
        actions = ["✅ Approve this card"]

        # Add sentence reselection for Cloze cards
        if isinstance(card, ClozeCard):
            actions.append("🔄 Change selected sentence")

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
            # Check if Cloze card has sentence selected before approving
            if isinstance(card, ClozeCard) and not card.selected_sentence:
                print(
                    "❌ Cannot approve Cloze card without selecting a sentence first."
                )
                continue
            card.mark_complete()
            logger.info("Card approved", word=card.word)
            break
        elif action.startswith("🔄"):
            if isinstance(card, ClozeCard):
                await select_sentence_for_cloze_card(card)
        elif action.startswith("🖼️"):
            await handle_image_regeneration(session, card)
        elif action.startswith("🔊"):
            await handle_audio_regeneration(session, card)
        elif action.startswith("🔈"):
            await handle_audio_replay(card)


async def display_card_media(card: Union[WordCard, ClozeCard]) -> None:
    """Display the generated media for a card."""
    if card.image_path and Path(card.image_path).exists():
        try:
            print(f"\nDisplaying image: {card.image_path}")
            view_image(str(card.image_path))
        except Exception as e:
            logger.error("Failed to display image", word=card.word, error=str(e))
            print(f"❌ Could not display image: {e}")
    else:
        print("❌ No image available")

    if card.audio_path and Path(card.audio_path).exists():
        print(f"🔊 Playing audio: {card.audio_path}")
        play_audio(Path(card.audio_path))
    else:
        print("❌ No audio available")


async def handle_image_regeneration(
    session: Session, card: Union[WordCard, ClozeCard]
) -> None:
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


async def handle_audio_regeneration(
    session: Session, card: Union[WordCard, ClozeCard]
) -> None:
    """Handle user request to regenerate audio."""
    print(f"\nRegenerating audio for '{card.word}'...")

    logger.info("Starting audio regeneration", word=card.word)

    success = await regenerate_audio(session, card)

    if success:
        print("✅ Audio regenerated successfully!")
        if card.audio_path:
            print(f"🔊 New audio: {card.audio_path}")
            play_audio(Path(card.audio_path))
    else:
        print("❌ Audio regeneration failed. Please try again.")


async def handle_audio_replay(card: Union[WordCard, ClozeCard]) -> None:
    """Handle user request to replay audio."""
    if card.audio_path and Path(card.audio_path).exists():
        print(f"\n🔈 Replaying audio for '{card.word}'...")
        play_audio(Path(card.audio_path))
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
