import csv
import re
import shutil
from pathlib import Path

from loguru import logger

from config import ClozeAnkiConfig
from models import ClozeCard, Session


def blank_word_in_sentence(sentence: str, target_word: str) -> str:
    """Replace target word in sentence with exactly 6 underscores."""
    # Create pattern to match word boundaries and various forms
    # This handles conjugations and inflections
    pattern = rf'\b{re.escape(target_word)}\w*\b'
    
    # Replace with exactly 6 underscores
    blanked_sentence = re.sub(pattern, "______", sentence, flags=re.IGNORECASE)
    
    logger.debug(
        "Word blanking applied",
        original=sentence,
        target_word=target_word,
        result=blanked_sentence
    )
    
    return blanked_sentence


def create_cloze_csv_row(card: ClozeCard, config: ClozeAnkiConfig) -> list[str]:
    """Create a CSV row for a single Cloze card."""
    
    # Field 1: Front (Example with word blanked out or missing)
    front_example = ""
    if card.selected_sentence:
        front_example = blank_word_in_sentence(card.selected_sentence, card.word)
    
    # Field 2: Front (Picture) - HTML img tag with UUID filename
    front_picture = ""
    if card.image_path:
        image_filename = f"{card.word.lower().replace(' ', '_')}-{card.short_id}.jpg"
        front_picture = f'<img src="{image_filename}">'
    
    # Field 3: Front (Definitions, base word, etc.)
    front_definitions = card.definitions or ""
    
    # Field 4: Back (a single word/phrase, no context)
    back_word = card.word
    
    # Field 5: - The full sentence (no words blanked out)
    full_sentence = card.selected_sentence or ""
    
    # Field 6: - Extra Info (Pronunciation, personal connections, conjugations, etc)
    extra_info_parts = []
    if card.ipa:
        extra_info_parts.append(card.ipa)
    if card.audio_path:
        audio_filename = f"{card.word.lower().replace(' ', '_')}-{card.short_id}.mp3"
        extra_info_parts.append(f"[sound:{audio_filename}]")
    if card.personal_context:
        extra_info_parts.append(card.personal_context)
    extra_info = " ".join(extra_info_parts)
    
    return [
        front_example,
        front_picture,
        front_definitions,
        back_word,
        full_sentence,
        extra_info,
    ]


def copy_cloze_media_files(session: Session, config: ClozeAnkiConfig) -> dict[str, bool]:
    """Copy approved Cloze card media files to Anki's collection.media folder."""
    if not config.anki_media_path:
        raise ValueError(
            "Anki collection.media path not found. Please specify manually."
        )

    if not config.anki_media_path.exists():
        raise ValueError(
            f"Anki collection.media path does not exist: {config.anki_media_path}"
        )

    copy_results = {}
    cloze_cards = session.cloze_cards

    for card in cloze_cards:
        if not card.is_complete:
            logger.warning("Skipping incomplete Cloze card", word=card.word)
            continue

        # Copy image file
        if card.image_path and Path(card.image_path).exists():
            image_filename = (
                f"{card.word.lower().replace(' ', '_')}-{card.short_id}.jpg"
            )
            dest_image = config.anki_media_path / image_filename

            try:
                shutil.copy2(card.image_path, dest_image)
                copy_results[f"{card.word}_image"] = True
                logger.info("Copied Cloze image to Anki", word=card.word, dest=dest_image)
            except Exception as e:
                copy_results[f"{card.word}_image"] = False
                logger.error("Failed to copy Cloze image", word=card.word, error=str(e))

        # Copy audio file
        if card.audio_path and Path(card.audio_path).exists():
            audio_filename = (
                f"{card.word.lower().replace(' ', '_')}-{card.short_id}.mp3"
            )
            dest_audio = config.anki_media_path / audio_filename

            try:
                shutil.copy2(card.audio_path, dest_audio)
                copy_results[f"{card.word}_audio"] = True
                logger.info("Copied Cloze audio to Anki", word=card.word, dest=dest_audio)
            except Exception as e:
                copy_results[f"{card.word}_audio"] = False
                logger.error("Failed to copy Cloze audio", word=card.word, error=str(e))

    return copy_results


def generate_cloze_csv(session: Session, config: ClozeAnkiConfig, output_path: Path) -> bool:
    """Generate Anki import CSV file for approved Cloze cards."""
    cloze_cards = session.cloze_cards
    incomplete_cloze_cards = [card for card in cloze_cards if not card.is_complete]
    
    if incomplete_cloze_cards:
        incomplete_count = len(incomplete_cloze_cards)
        logger.error(
            "Cannot export incomplete Cloze cards", incomplete_cards=incomplete_count
        )
        return False

    if not cloze_cards:
        logger.info("No Cloze cards to export")
        return True

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            # Write headers for Anki import
            csvfile.write(f"#notetype:{config.NOTE_TYPE}\n")
            csvfile.write(f"#deck:{config.deck_name}\n")
            csvfile.write("#separator:tab\n")
            csvfile.write("#html:true\n")
            # Note: Cloze cards don't use GUID for duplicate prevention

            # Write field names header (with #fields: prefix so Anki knows it's headers)
            csvfile.write("#fields:" + "\t".join(config.FIELD_NAMES) + "\n")

            # Write card data
            writer = csv.writer(csvfile, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

            for card in cloze_cards:
                if card.is_complete:
                    row = create_cloze_csv_row(card, config)
                    writer.writerow(row)
                    logger.debug("Added Cloze card to CSV", word=card.word)

        logger.info(
            "Cloze CSV generated successfully", 
            path=output_path, 
            cards=len(cloze_cards)
        )
        return True

    except Exception as e:
        logger.error("Failed to generate Cloze CSV", error=str(e))
        return False


def export_cloze_cards_to_anki(
    session: Session, config: ClozeAnkiConfig | None = None, csv_path: Path | None = None
) -> bool:
    """Complete export process for Cloze cards: copy media files and generate CSV."""
    if config is None:
        config = ClozeAnkiConfig()

    if csv_path is None:
        csv_path = session.output_directory / "anki_import_cloze.csv"

    cloze_cards = session.cloze_cards
    logger.info("Starting Cloze card export", cards=len(cloze_cards))

    if not cloze_cards:
        logger.info("No Cloze cards to export")
        return True

    # Verify all Cloze cards are complete
    incomplete_cloze_cards = [card for card in cloze_cards if not card.is_complete]
    if incomplete_cloze_cards:
        incomplete_words = [card.word for card in incomplete_cloze_cards]
        logger.error(
            "Cannot export: incomplete Cloze cards found", 
            incomplete_cards=incomplete_words
        )
        return False

    # Copy media files to Anki
    logger.info("Copying Cloze media files to Anki")
    try:
        copy_results = copy_cloze_media_files(session, config)
        failed_copies = [k for k, v in copy_results.items() if not v]
        if failed_copies:
            logger.warning("Some Cloze media files failed to copy", failed=failed_copies)
    except Exception as e:
        logger.error("Cloze media copy failed", error=str(e))
        return False

    # Generate CSV file
    logger.info("Generating Cloze CSV file")
    success = generate_cloze_csv(session, config, csv_path)

    if success:
        logger.info("Cloze card export completed successfully", csv_path=csv_path)
        print("\n✅ Cloze card export complete!")
        print(f"📁 CSV file: {csv_path}")
        print(f"📁 Media copied to: {config.anki_media_path}")
        print(f"📊 Cloze cards exported: {len(cloze_cards)}")
        print("\nTo import in Anki:")
        print("  1. Open Anki")
        print("  2. File → Import")
        print(f"  3. Select: {csv_path}")
        print("  4. Verify settings and import")

    return success