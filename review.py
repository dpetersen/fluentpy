import subprocess
import shutil
from pathlib import Path

import questionary
from loguru import logger
from openai import AsyncOpenAI

from images import view_image
from models import Session, WordCard, ClozeCard, WordInput, ClozeCardInput
from typing import Union
from session import regenerate_audio, regenerate_image
from mnemonic_images import (
    generate_mnemonic_image,
    get_mnemonic_filename,
    check_mnemonic_exists,
)


async def review_session(session: Session, auto_approve: bool = False) -> None:
    """Interactive review of all cards in the session until all are approved."""
    logger.info(
        "Starting session review",
        total_cards=len(session.cards),
        auto_approve=auto_approve,
    )

    if auto_approve:
        # Auto-approve all cards for testing
        for card in session.cards:
            card.mark_complete()
        logger.info("Auto-approved all cards")
        return

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
            # For Cloze cards with selected sentences, show the word form instead of base word
            display_word = card.word
            if isinstance(card, ClozeCard) and card.selected_word_form:
                # Show base verb in parentheses if enabled for verb cards
                if card.show_base_verb and card.verb_type:
                    display_parts = [f"{card.selected_word_form} ({card.word})"]
                else:
                    display_parts = [card.selected_word_form]
                context_parts = []
                if card.selected_subject:
                    context_parts.append(card.selected_subject)
                if card.selected_tense:
                    context_parts.append(card.selected_tense)
                if context_parts:
                    display_parts.append(f"[{', '.join(context_parts)}]")
                display_word = " ".join(display_parts)
            choice_text = f"{card_type_indicator} {display_word} - {card.ipa} ({card.part_of_speech})"
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
            selected_sentences = await select_sentences_for_cloze_card(selected_card)
            if selected_sentences:
                # Use the first selected sentence for this card
                selected_card.selected_sentence = selected_sentences[0][0]
                selected_card.selected_word_form = selected_sentences[0][1]
                selected_card.selected_word_ipa = selected_sentences[0][2]
                selected_card.selected_tense = selected_sentences[0][3]
                selected_card.selected_subject = selected_sentences[0][4]

        # Review the selected card
        await review_card(session, selected_card)

    logger.info("All cards approved! Session review complete.")


async def select_sentences_for_cloze_card(
    card: ClozeCard,
) -> list[tuple[str, str, str, str | None, str | None]]:
    """Let user select one or more sentences from the example sentences for Cloze cards.

    Returns a list of tuples (sentence, word_form, ipa, tense, subject) for each selected sentence.
    """
    logger.info(
        "Starting sentence selection",
        word=card.word,
        sentence_count=len(card.example_sentences),
    )

    print(f"\n🧩 Choose sentences for '{card.word}':")
    print("(Select one or more sentences to create multiple cards)")

    # Create sentence choices for questionary
    sentence_choices = []
    for i, sentence_data in enumerate(card.example_sentences, 1):
        sentence_text = sentence_data["sentence"]
        word_form = sentence_data["word_form"]
        ipa = sentence_data.get("ipa", "")
        tense = sentence_data.get("tense")
        subject = sentence_data.get("subject")

        # Build the display text with tense and subject information
        display_parts = [f"{i}. {sentence_text}"]
        info_parts = [f"uses: {word_form}"]
        if ipa:
            info_parts.append(f"IPA: {ipa}")
        if subject:
            info_parts.append(f"subject: {subject}")
        if tense:
            info_parts.append(f"tense: {tense}")
        display_parts.append(f"({', '.join(info_parts)})")

        sentence_choices.append(
            {
                "name": " ".join(display_parts),
                "value": i - 1,  # Store the index for easy lookup
            }
        )

    # Let user select multiple sentences
    selected_indices = await questionary.checkbox(
        "Select sentences (space to select, enter to confirm):",
        choices=sentence_choices,
    ).ask_async()

    if not selected_indices:
        # If no selection, prompt to select at least one
        print("⚠️  Please select at least one sentence.")
        selected_index = await questionary.select(
            "Select a sentence:",
            choices=[choice["name"] for choice in sentence_choices],
        ).ask_async()
        # Extract index from the selection
        selected_indices = [int(selected_index.split(".", 1)[0]) - 1]

    # Extract selected sentences
    selected_sentences = []
    for index in selected_indices:
        sentence_data = card.example_sentences[index]
        tense = sentence_data.get("tense")
        subject = sentence_data.get("subject")
        ipa = sentence_data.get("ipa", "")
        selected_sentences.append(
            (sentence_data["sentence"], sentence_data["word_form"], ipa, tense, subject)
        )

        logger.info(
            "Sentence selected",
            word=card.word,
            selected_sentence=sentence_data["sentence"],
            word_form=sentence_data["word_form"],
            tense=tense,
            subject=subject,
            index=index + 1,
        )

    print(f"\n✅ Selected {len(selected_sentences)} sentence(s):")
    for sentence, word_form, ipa, tense, subject in selected_sentences:
        info_parts = [f"uses: {word_form}"]
        if subject:
            info_parts.append(f"subject: {subject}")
        if tense:
            info_parts.append(f"tense: {tense}")
        print(f"   • {sentence} ({', '.join(info_parts)})")
    print()

    return selected_sentences


def display_card_info(card: Union[WordCard, ClozeCard]) -> None:
    """Display card information header."""
    print(f"\n{'=' * 60}")
    card_type_icon = "🧩" if isinstance(card, ClozeCard) else "📚"

    # For Cloze cards, show the word form if available
    display_word = card.word
    if isinstance(card, ClozeCard) and card.selected_word_form:
        if card.show_base_verb and card.verb_type:
            display_word = f"{card.selected_word_form} ({card.word})"
        else:
            display_word = f"{card.selected_word_form} (from {card.word})"

    print(f"{card_type_icon} {card.card_type.title()} Card: {display_word}")
    # For Cloze cards with selected word form, show the conjugated IPA
    if isinstance(card, ClozeCard) and card.selected_word_ipa:
        print(f"IPA: {card.selected_word_ipa}")
    else:
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
            if card.selected_subject:
                print(f"Subject: {card.selected_subject}")
            if card.selected_tense:
                print(f"Tense: {card.selected_tense}")
        else:
            print("⚠️  No sentence selected yet")

    print(f"{'=' * 60}")


async def review_card(session: Session, card: Union[WordCard, ClozeCard]) -> None:
    """Review a single card and allow user to approve or regenerate media."""
    logger.info("Reviewing card", word=card.word, card_type=card.card_type)

    # Display card information
    display_card_info(card)

    # Display generated media
    await display_card_media(card)

    # Review loop for this card
    while True:
        actions = ["✅ Approve this card"]

        # Add sentence reselection for Cloze cards
        if isinstance(card, ClozeCard):
            actions.append("🔄 Change selected sentence")

            # Add base verb toggle for verb cards
            if card.verb_type:
                toggle_text = (
                    "👁️  Base verb: shown"
                    if card.show_base_verb
                    else "👁️  Base verb: hidden"
                )
                actions.append(toggle_text)

        # Always show regenerate image option - allows fixing failed generations
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

            # Check if card has required media files
            missing_media = []
            if not card.image_path or not Path(card.image_path).exists():
                missing_media.append("image")
            if not card.audio_path or not Path(card.audio_path).exists():
                missing_media.append("audio")

            if missing_media:
                print(
                    f"❌ Cannot approve card without {' and '.join(missing_media)}. "
                    f"Please regenerate the missing media first."
                )
                continue

            card.mark_complete()
            logger.info("Card approved", word=card.word)
            break
        elif action.startswith("🔄"):
            if isinstance(card, ClozeCard):
                selected_sentences = await select_sentences_for_cloze_card(card)
                if selected_sentences:
                    # Update the card with the first selected sentence
                    card.selected_sentence = selected_sentences[0][0]
                    card.selected_word_form = selected_sentences[0][1]
                    card.selected_word_ipa = selected_sentences[0][2]
                    card.selected_tense = selected_sentences[0][3]
                    card.selected_subject = selected_sentences[0][4]
        elif action.startswith("🖼️"):
            await handle_image_regeneration(session, card)
        elif action.startswith("🔊"):
            await handle_audio_regeneration(session, card)
        elif action.startswith("🔈"):
            await handle_audio_replay(card)
        elif action.startswith("👁️"):
            # Toggle base verb display for cloze cards
            if isinstance(card, ClozeCard) and card.verb_type:
                card.show_base_verb = not card.show_base_verb
                logger.info(
                    "Toggled base verb display",
                    word=card.word,
                    show_base_verb=card.show_base_verb,
                )
                # Redisplay the card information with the new state
                display_card_info(card)
                await display_card_media(card)


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
    # Show conjugated form for cloze cards
    display_word = card.word
    if isinstance(card, ClozeCard) and card.selected_word_form:
        display_word = f"{card.selected_word_form} (from {card.word})"
    print(f"\nRegenerating image for '{display_word}'...")

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
    # Show conjugated form for cloze cards
    display_word = card.word
    if isinstance(card, ClozeCard) and card.selected_word_form:
        display_word = f"{card.selected_word_form} (from {card.word})"
    print(f"\nRegenerating audio for '{display_word}'...")

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
        # Show conjugated form for cloze cards
        display_word = card.word
        if isinstance(card, ClozeCard) and card.selected_word_form:
            display_word = f"{card.selected_word_form} (from {card.word})"
        print(f"\n🔈 Replaying audio for '{display_word}'...")
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

        # Show word form for Cloze cards with selected sentences
        display_word = card.word
        if isinstance(card, ClozeCard) and card.selected_word_form:
            display_parts = [f"{card.selected_word_form} ({card.word})"]
            if card.selected_tense:
                display_parts.append(f"[{card.selected_tense}]")
            display_word = " ".join(display_parts)

        # Show conjugated IPA for cloze cards if available
        display_ipa = (
            card.selected_word_ipa
            if isinstance(card, ClozeCard) and card.selected_word_ipa
            else card.ipa
        )
        print(f"  {status} {display_word} ({display_ipa}) {' '.join(media_status)}")

    print(f"\nAll media files are saved in: {session.output_directory}")
    print("Ready for Anki export!")
    print(f"{'=' * 60}")


async def review_mnemonic_images(
    word_inputs: list[Union[WordInput, ClozeCardInput]],
    anki_media_path: Path,
    client: AsyncOpenAI,
) -> set[str]:
    """Review and generate mnemonic priming images.

    Returns a set of words that have mnemonic images (either existing or newly generated).
    """
    logger.info("Starting mnemonic image review")
    words_with_mnemonic: set[str] = set()

    # First, collect all words that need mnemonic generation or already have one
    words_needing_generation: list[tuple[str, str]] = []  # (word, description)

    for word_input in word_inputs:
        word = word_input.word

        # Check if mnemonic already exists
        if check_mnemonic_exists(word, anki_media_path):
            if word_input.mnemonic_image_description:
                # User wants to replace existing
                words_needing_generation.append(
                    (word, word_input.mnemonic_image_description)
                )
            else:
                # Keep existing
                words_with_mnemonic.add(word)
                logger.info(f"Using existing mnemonic image for '{word}'")
        elif word_input.mnemonic_image_description:
            # New mnemonic requested
            words_needing_generation.append(
                (word, word_input.mnemonic_image_description)
            )

    if not words_needing_generation:
        logger.info("No mnemonic images to generate or review")
        return words_with_mnemonic

    print("\n=== Mnemonic Image Review ===")
    print(f"Generating mnemonic images for {len(words_needing_generation)} words...\n")

    # Review each mnemonic image
    for i, (word, description) in enumerate(words_needing_generation, 1):
        print(f"[{i}/{len(words_needing_generation)}] Generating mnemonic for: {word}")
        print(f'Description: "{description}"')

        # Generate to temp location first
        temp_path = anki_media_path.parent / f"temp_mpi_{word}.jpg"

        try:
            await generate_mnemonic_image(
                client=client,
                word=word,
                description=description,
                output_path=temp_path,
            )

            # Display the image
            view_image(str(temp_path))

            # Get user approval
            choices = [
                "Approve",
                "Regenerate with additional context",
                "Skip (no mnemonic image)",
            ]
            action = await questionary.select(
                "Choose action:",
                choices=choices,
            ).ask_async()

            if action == "Approve":
                # Copy to final location
                final_path = anki_media_path / get_mnemonic_filename(word)
                shutil.copy2(temp_path, final_path)
                words_with_mnemonic.add(word)
                logger.info(
                    f"✓ Mnemonic image saved to Anki: {get_mnemonic_filename(word)}"
                )
                print(
                    f"✓ Mnemonic image saved to Anki: {get_mnemonic_filename(word)}\n"
                )

            elif action == "Regenerate with additional context":
                # Allow regeneration with additional context
                while True:
                    additional_context = await questionary.text(
                        "Additional context:",
                        validate=lambda text: bool(text.strip()),
                    ).ask_async()

                    full_description = f"{description}. {additional_context}"
                    print("🔄 Regenerating...")

                    # Regenerate
                    await generate_mnemonic_image(
                        client=client,
                        word=word,
                        description=full_description,
                        output_path=temp_path,
                    )

                    # Display again
                    view_image(str(temp_path))

                    # Ask again
                    action = await questionary.select(
                        "Choose action:",
                        choices=[
                            "Approve",
                            "Regenerate with additional context",
                            "Skip (no mnemonic image)",
                        ],
                    ).ask_async()

                    if action == "Approve":
                        final_path = anki_media_path / get_mnemonic_filename(word)
                        shutil.copy2(temp_path, final_path)
                        words_with_mnemonic.add(word)
                        logger.info(
                            f"✓ Mnemonic image saved to Anki: {get_mnemonic_filename(word)}"
                        )
                        print(
                            f"✓ Mnemonic image saved to Anki: {get_mnemonic_filename(word)}\n"
                        )
                        break
                    elif action == "Skip (no mnemonic image)":
                        logger.info(f"Skipped mnemonic image for '{word}'")
                        print(f"❌ Skipped mnemonic image for '{word}'\n")
                        break
                    # Otherwise loop continues for another regeneration

            else:  # Skip
                logger.info(f"Skipped mnemonic image for '{word}'")
                print(f"❌ Skipped mnemonic image for '{word}'\n")

        except Exception as e:
            logger.error(f"Failed to generate mnemonic for '{word}': {e}")
            print(f"❌ Error generating mnemonic for '{word}': {e}\n")
        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    print("Mnemonic image review complete!")
    print(f"{len(words_with_mnemonic)} words have mnemonic images\n")

    return words_with_mnemonic
