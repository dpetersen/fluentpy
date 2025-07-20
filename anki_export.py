import csv
import shutil
from pathlib import Path

from loguru import logger

from config import AnkiConfig
from models import Session, WordCard, ClozeCard
from typing import Union


def create_field_3_content(card: Union[WordCard, ClozeCard], config: AnkiConfig) -> str:
    """Create content for field 3: Gender, Personal Connection, Extra Info."""
    parts = []

    # Add Spanish part of speech
    spanish_pos = config.get_spanish_part_of_speech(card.part_of_speech)

    # Add gender for nouns, verb type for verbs
    if card.part_of_speech == "noun" and card.gender:
        spanish_gender = config.get_spanish_gender(card.gender)
        parts.append(f"{spanish_pos} {spanish_gender}")
    elif card.part_of_speech == "verb" and card.verb_type:
        spanish_verb_type = config.get_spanish_verb_type(card.verb_type)
        parts.append(f"{spanish_pos} {spanish_verb_type}")
    else:
        parts.append(spanish_pos)

    # Add personal context if provided
    if card.personal_context:
        if parts:
            parts.append(card.personal_context)
        else:
            parts.append(card.personal_context)

    return ". ".join(parts) + "." if parts else ""


def create_csv_row(card: Union[WordCard, ClozeCard], config: AnkiConfig) -> list[str]:
    """Create a CSV row for a single card."""
    # Field 1: Word
    word = card.word

    # Field 2: Picture (HTML img tag with UUID filename)
    picture = ""
    if card.image_path:
        image_filename = f"{card.word.lower().replace(' ', '_')}-{card.short_id}.jpg"
        picture = f'<img src="{image_filename}">'

    # Field 3: Gender, Personal Connection, Extra Info
    field_3 = create_field_3_content(card, config)

    # Field 4: Pronunciation (audio + IPA)
    pronunciation_parts = []
    if card.audio_path:
        audio_filename = f"{card.word.lower().replace(' ', '_')}-{card.short_id}.mp3"
        pronunciation_parts.append(f"[sound:{audio_filename}]")

    # Use conjugated IPA for cloze cards if available
    if isinstance(card, ClozeCard) and card.selected_word_ipa:
        pronunciation_parts.append(card.selected_word_ipa)
    elif card.ipa:
        pronunciation_parts.append(card.ipa)
    pronunciation = " ".join(pronunciation_parts)

    # Field 5: Test Spelling
    test_spelling = "y" if config.test_spelling else ""

    # Field 6: GUID
    guid = card.guid

    return [word, picture, field_3, pronunciation, test_spelling, guid]


def copy_media_files(session: Session, config: AnkiConfig) -> dict[str, bool]:
    """Copy approved media files to Anki's collection.media folder."""
    if not config.anki_media_path:
        raise ValueError(
            "Anki collection.media path not found. Please specify manually."
        )

    if not config.anki_media_path.exists():
        raise ValueError(
            f"Anki collection.media path does not exist: {config.anki_media_path}"
        )

    copy_results = {}

    for card in session.vocabulary_cards:
        if not card.is_complete:
            logger.warning("Skipping incomplete card", word=card.word)
            continue

        # Copy image file
        if card.image_path and Path(card.image_path).exists():
            image_filename = (
                f"{card.word.lower().replace(' ', '_')}-{card.short_id}.jpg"
            )
            dest_image = config.anki_media_path / image_filename

            try:
                shutil.copy2(Path(card.image_path), dest_image)
                copy_results[f"{card.word}_image"] = True
                logger.info("Copied image to Anki", word=card.word, dest=dest_image)
            except Exception as e:
                copy_results[f"{card.word}_image"] = False
                logger.error("Failed to copy image", word=card.word, error=str(e))

        # Copy audio file
        if card.audio_path and Path(card.audio_path).exists():
            audio_filename = (
                f"{card.word.lower().replace(' ', '_')}-{card.short_id}.mp3"
            )
            dest_audio = config.anki_media_path / audio_filename

            try:
                shutil.copy2(Path(card.audio_path), dest_audio)
                copy_results[f"{card.word}_audio"] = True
                logger.info("Copied audio to Anki", word=card.word, dest=dest_audio)
            except Exception as e:
                copy_results[f"{card.word}_audio"] = False
                logger.error("Failed to copy audio", word=card.word, error=str(e))

    return copy_results


def generate_csv(session: Session, config: AnkiConfig, output_path: Path) -> bool:
    """Generate Anki import CSV file for approved vocabulary cards."""
    incomplete_vocab_cards = [
        card for card in session.vocabulary_cards if not card.is_complete
    ]
    if incomplete_vocab_cards:
        incomplete_count = len(incomplete_vocab_cards)
        logger.error(
            "Cannot export incomplete vocabulary cards",
            incomplete_cards=incomplete_count,
        )
        return False

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            # Write headers for Anki import
            csvfile.write(f"#notetype:{config.NOTE_TYPE}\n")
            csvfile.write(f"#deck:{config.deck_name}\n")
            csvfile.write("#separator:tab\n")
            csvfile.write("#html:true\n")
            csvfile.write("#guid column:6\n")

            # Write field names header (with #fields: prefix so Anki knows it's headers)
            csvfile.write("#fields:" + "\t".join(config.FIELD_NAMES) + "\n")

            # Write card data
            writer = csv.writer(csvfile, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

            # Write only vocabulary cards (not cloze cards)
            for card in session.vocabulary_cards:
                if card.is_complete:
                    row = create_csv_row(card, config)
                    writer.writerow(row)
                    logger.debug(
                        "Added card to CSV", word=card.word, card_type=card.card_type
                    )

        logger.info(
            "CSV generated successfully",
            path=output_path,
            cards=len(session.vocabulary_cards),
        )
        return True

    except Exception as e:
        logger.error("Failed to generate CSV", error=str(e))
        return False


def export_to_anki(
    session: Session, config: AnkiConfig | None = None, csv_path: Path | None = None
) -> bool:
    """Complete export process: copy media files and generate CSV."""
    if config is None:
        config = AnkiConfig()

    if csv_path is None:
        csv_path = session.output_directory / "anki_import.csv"

    logger.info("Starting Anki export", cards=len(session.vocabulary_cards))

    # Verify all vocabulary cards are complete
    incomplete_vocab_cards = [
        card for card in session.vocabulary_cards if not card.is_complete
    ]
    if incomplete_vocab_cards:
        incomplete_words = [card.word for card in incomplete_vocab_cards]
        logger.error(
            "Cannot export: incomplete vocabulary cards found",
            incomplete_cards=incomplete_words,
        )
        return False

    # Copy media files to Anki
    logger.info("Copying media files to Anki")
    try:
        copy_results = copy_media_files(session, config)
        failed_copies = [k for k, v in copy_results.items() if not v]
        if failed_copies:
            logger.warning("Some media files failed to copy", failed=failed_copies)
    except Exception as e:
        logger.error("Media copy failed", error=str(e))
        return False

    # Generate CSV file
    logger.info("Generating CSV file")
    success = generate_csv(session, config, csv_path)

    if success:
        logger.info("Anki export completed successfully", csv_path=csv_path)
        print("\n✅ Export complete!")
        print(f"📁 CSV file: {csv_path}")
        print(f"📁 Media copied to: {config.anki_media_path}")
        print(f"📊 Cards exported: {len(session.vocabulary_cards)}")
        print("\nReady to import in Anki:")
        print("  1. Open Anki")
        print("  2. File → Import")
        print(f"  3. Select: {csv_path}")
        print("  4. Verify settings and import")

    return success
