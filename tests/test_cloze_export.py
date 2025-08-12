"""Test cloze card export functionality."""

import csv
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from config import ClozeAnkiConfig
from cloze_export import export_cloze_cards_to_anki
from models import ClozeCard, Session


@pytest.fixture
def cloze_config():
    """Create a test ClozeAnkiConfig."""
    return ClozeAnkiConfig(
        deck_name="Test Deck",
        anki_media_path=Path("/fake/collection/media"),
    )


@pytest.fixture
def sample_cloze_card():
    """Create a sample ClozeCard for testing."""
    return ClozeCard(
        word="casa",
        guid=str(uuid.uuid4()),
        word_analysis={
            "ipa": "ˈka.sa",
            "part_of_speech": "sustantivo",
            "gender": "femenino",
            "example_sentences": [
                {"sentence": "La casa es muy grande.", "word_form": "casa"},
                {"sentence": "Vivo en una casa blanca.", "word_form": "casa"},
                {"sentence": "Mi casa tiene jardín.", "word_form": "casa"},
            ],
        },
        selected_sentence="La casa es muy grande.",
        selected_word_form="casa",
        image_path="casa-abc123.jpg",
        audio_path="casa-abc123.mp3",
        memory_aid="Think of your childhood home",
        extra_prompt="Add some flowers in the garden",
    )


@pytest.fixture
def session_with_cloze_cards(sample_cloze_card):
    """Create a session with sample ClozeCards."""
    return Session(
        vocabulary_cards=[],
        cloze_cards=[sample_cloze_card],
        output_directory=Path("test_output"),
    )


def test_export_cloze_cards_to_anki_creates_csv(
    session_with_cloze_cards, cloze_config, tmp_path
):
    """Test that export_cloze_cards_to_anki creates the expected CSV file."""
    # Override config paths to use tmp_path
    cloze_config.anki_media_path = tmp_path / "collection_media"
    session_with_cloze_cards.output_directory = tmp_path

    # Create the collection media directory
    cloze_config.anki_media_path.mkdir(parents=True)

    # Create mock media files
    card = session_with_cloze_cards.cloze_cards[0]
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    # Mark card as complete
    card.mark_complete()

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"casa_image": True, "casa_audio": True}
        result = export_cloze_cards_to_anki(session_with_cloze_cards, cloze_config)

    assert result is True

    # Check CSV file was created
    csv_path = tmp_path / "anki_import_cloze.csv"
    assert csv_path.exists()

    # Check CSV content
    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert content.startswith("#notetype:")
    assert "#deck:Test Deck" in content
    assert "#fields:" in content
    assert "casa" in content
    assert (
        "La ______ es muy grande." in content
    )  # Cloze export uses ______ not {{c1::}}

    # Verify media copying was called
    assert mock_copy.call_count == 1


def test_export_cloze_cards_csv_headers(
    session_with_cloze_cards, cloze_config, tmp_path
):
    """Test that CSV has correct headers with #fields: prefix."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    session_with_cloze_cards.output_directory = tmp_path

    cloze_config.anki_media_path.mkdir(parents=True)

    card = session_with_cloze_cards.cloze_cards[0]
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    # Mark card as complete
    card.mark_complete()

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"casa_image": True, "casa_audio": True}
        export_cloze_cards_to_anki(session_with_cloze_cards, cloze_config)

    csv_path = tmp_path / "anki_import_cloze.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        # Find the #fields: line
        fields_line = None
        for line in f:
            if line.startswith("#fields:"):
                fields_line = line.strip()
                break

    expected_fields = [
        "Front (Example with word blanked out or missing)",
        "Front (Picture)",
        "Front (Definitions, base word, etc.)",
        "Back (a single word/phrase, no context)",
        "- The full sentence (no words blanked out)",
        "- Extra Info (Pronunciation, personal connections, conjugations, etc)",
        "",  # Field 7 - empty
        "",  # Field 8 - empty
        "",  # Field 9 - empty
        "Mnemonic Priming Image",  # Field 10
    ]
    expected_header = "#fields:" + "\t".join(expected_fields)
    assert fields_line == expected_header


def test_export_cloze_cards_csv_content(
    session_with_cloze_cards, cloze_config, tmp_path
):
    """Test that CSV content matches expected format."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    session_with_cloze_cards.output_directory = tmp_path

    cloze_config.anki_media_path.mkdir(parents=True)

    card = session_with_cloze_cards.cloze_cards[0]
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    # Mark card as complete
    card.mark_complete()

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"casa_image": True, "casa_audio": True}
        export_cloze_cards_to_anki(session_with_cloze_cards, cloze_config)

    csv_path = tmp_path / "anki_import_cloze.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        # Skip the header lines
        for line in f:
            if line.startswith("#fields:"):
                break
        # Now read the actual data
        reader = csv.reader(f, delimiter="\t")
        row = next(reader)

    # Check the 6 fields according to ClozeAnkiConfig.FIELD_NAMES
    assert row[0] == "La ______ es muy grande."  # Front (Example with word blanked out)
    assert f'<img src="casa-{card.short_id}.jpg">' in row[1]  # Front (Picture)
    assert (
        row[2] == "Think of your childhood home"
    )  # Front (Definitions) - only memory_aid, no verb info (casa is a noun)
    assert row[3] == "casa"  # Back (a single word/phrase)
    assert row[4] == "La casa es muy grande."  # Full sentence (no audio)
    assert "ˈka.sa" in row[5]  # Extra Info (contains IPA)


def test_export_cloze_cards_no_cards(cloze_config, tmp_path):
    """Test export with no Cloze cards."""

    session = Session(
        vocabulary_cards=[],
        cloze_cards=[],
        output_directory=Path("test_output"),
    )

    result = export_cloze_cards_to_anki(session, cloze_config)
    assert result is True

    # When there are no cards, CSV should not be created
    csv_path = tmp_path / "anki_import_cloze.csv"
    assert not csv_path.exists()


def test_export_cloze_cards_missing_media_files(
    session_with_cloze_cards, cloze_config, tmp_path
):
    """Test export handling of missing media files."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    session_with_cloze_cards.output_directory = tmp_path

    cloze_config.anki_media_path.mkdir(parents=True)

    # Don't create media files to simulate missing files
    # But mark the card as complete
    card = session_with_cloze_cards.cloze_cards[0]
    card.mark_complete()

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {
            "casa_image": False,
            "casa_audio": False,
        }  # Simulate copy failure but return dict
        result = export_cloze_cards_to_anki(session_with_cloze_cards, cloze_config)

    # Export should still succeed even if media copying fails
    assert result is True

    # CSV should still be created
    csv_path = tmp_path / "anki_import_cloze.csv"
    assert csv_path.exists()


def test_export_cloze_cards_multiple_cards(cloze_config, tmp_path):
    """Test export with multiple Cloze cards."""
    cloze_config.anki_media_path = tmp_path / "collection_media"

    cloze_config.anki_media_path.mkdir(parents=True)

    # Create multiple cards
    cards = []
    for i, word in enumerate(["casa", "perro", "libro"]):
        card = ClozeCard(
            word=word,
            guid=str(uuid.uuid4()),
            word_analysis={
                "ipa": f"ˈ{word}",
                "part_of_speech": "sustantivo",
                "gender": "masculino" if word != "casa" else "femenino",
                "example_sentences": [
                    {"sentence": f"Sentence with {word}.", "word_form": word}
                ],
            },
            selected_sentence=f"Sentence with {word}.",
            selected_word_form=word,
            image_path=f"{word}-{i}.jpg",
            audio_path=f"{word}-{i}.mp3",
        )
        cards.append(card)

        # Create mock media files
        image_path = tmp_path / card.image_path
        audio_path = tmp_path / card.audio_path
        image_path.write_text(f"fake image {i}")
        audio_path.write_text(f"fake audio {i}")

        # Mark card as complete
        card.mark_complete()

    session = Session(
        vocabulary_cards=[],
        cloze_cards=cards,
        output_directory=tmp_path,
    )

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {
            "casa_image": True,
            "casa_audio": True,
            "perro_image": True,
            "perro_audio": True,
            "libro_image": True,
            "libro_audio": True,
        }
        result = export_cloze_cards_to_anki(session, cloze_config)

    assert result is True

    csv_path = tmp_path / "anki_import_cloze.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Should have headers + 3 data rows (multiple header lines in Anki format)
    assert len(lines) == 8  # 5 header lines + 3 data rows

    # Check that all words are present
    content = "".join(lines)
    for word in ["casa", "perro", "libro"]:
        assert word in content
        assert "______" in content  # Check that blanking is present


def test_export_cloze_cards_error_handling(
    session_with_cloze_cards, cloze_config, tmp_path
):
    """Test export error handling."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    session_with_cloze_cards.output_directory = tmp_path

    # Create collection media directory
    cloze_config.anki_media_path.mkdir(parents=True)

    card = session_with_cloze_cards.cloze_cards[0]
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"casa_image": True, "casa_audio": True}

        # Make the output directory read-only to trigger an error
        tmp_path.chmod(0o444)

        try:
            result = export_cloze_cards_to_anki(session_with_cloze_cards, cloze_config)
            # Should return False on error
            assert result is False
        finally:
            # Restore permissions for cleanup
            tmp_path.chmod(0o755)


def test_cloze_export_verb_with_user_definitions(cloze_config, tmp_path):
    """Test export of verb cloze card with user-provided definitions."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    cloze_config.anki_media_path.mkdir(parents=True)

    # Create a verb card with user definitions
    card = ClozeCard(
        word="hablar",
        guid=str(uuid.uuid4()),
        word_analysis={
            "ipa": "aˈβlaɾ",
            "part_of_speech": "verbo",
            "gender": None,
            "verb_type": "intransitive",
            "example_sentences": [
                {
                    "sentence": "Yo hablo español.",
                    "word_form": "hablo",
                    "tense": "presente",
                }
            ],
        },
        selected_sentence="Yo hablo español.",
        selected_word_form="hablo",
        selected_tense="presente",
        selected_subject="yo",
        image_path="hablar-test123.jpg",
        audio_path="hablar-test123.mp3",
        memory_aid="To speak, think of someone talking",
    )
    card.mark_complete()

    # Create mock media files
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    session = Session(
        vocabulary_cards=[],
        cloze_cards=[card],
        output_directory=tmp_path,
    )

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"hablar_image": True, "hablar_audio": True}
        export_cloze_cards_to_anki(session, cloze_config)

    csv_path = tmp_path / "anki_import_cloze.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        # Skip headers
        for line in f:
            if line.startswith("#fields:"):
                break
        reader = csv.reader(f, delimiter="\t")
        row = next(reader)

    # Check Field 3 has user definition + verb info
    assert row[2] == "To speak, think of someone talking - intransitive, yo, presente"


def test_cloze_export_verb_without_user_definitions(cloze_config, tmp_path):
    """Test export of verb cloze card without user-provided definitions."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    cloze_config.anki_media_path.mkdir(parents=True)

    # Create a verb card without user definitions
    card = ClozeCard(
        word="comer",
        guid=str(uuid.uuid4()),
        word_analysis={
            "ipa": "koˈmeɾ",
            "part_of_speech": "verbo",
            "gender": None,
            "verb_type": "transitive",
            "example_sentences": [
                {
                    "sentence": "Ella come manzanas.",
                    "word_form": "come",
                    "tense": "presente",
                }
            ],
        },
        selected_sentence="Ella come manzanas.",
        selected_word_form="come",
        selected_tense="presente",
        selected_subject="ella",
        image_path="comer-test456.jpg",
        audio_path="comer-test456.mp3",
        memory_aid=None,  # No user definitions
    )
    card.mark_complete()

    # Create mock media files
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    session = Session(
        vocabulary_cards=[],
        cloze_cards=[card],
        output_directory=tmp_path,
    )

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"comer_image": True, "comer_audio": True}
        export_cloze_cards_to_anki(session, cloze_config)

    csv_path = tmp_path / "anki_import_cloze.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        # Skip headers
        for line in f:
            if line.startswith("#fields:"):
                break
        reader = csv.reader(f, delimiter="\t")
        row = next(reader)

    # Check Field 3 has only verb info (no user definition)
    assert row[2] == "transitive, ella, presente"


def test_cloze_export_verb_with_show_base_verb(cloze_config, tmp_path):
    """Test export of verb cloze card with show_base_verb enabled."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    cloze_config.anki_media_path.mkdir(parents=True)

    # Create a verb card with show_base_verb enabled
    card = ClozeCard(
        word="escribir",
        guid=str(uuid.uuid4()),
        word_analysis={
            "ipa": "es.kɾi.ˈβiɾ",
            "part_of_speech": "verbo",
            "gender": None,
            "verb_type": "regular",
            "example_sentences": [
                {
                    "sentence": "Yo escribo cartas.",
                    "word_form": "escribo",
                    "tense": "presente",
                }
            ],
        },
        selected_sentence="Yo escribo cartas.",
        selected_word_form="escribo",
        selected_tense="presente",
        selected_subject="yo",
        image_path="escribir-test789.jpg",
        audio_path="escribir-test789.mp3",
        memory_aid="To write, think of pen and paper",
        show_base_verb=True,  # Enable showing base verb
    )
    card.mark_complete()

    # Create mock media files
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    session = Session(
        vocabulary_cards=[],
        cloze_cards=[card],
        output_directory=tmp_path,
    )

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"escribir_image": True, "escribir_audio": True}
        export_cloze_cards_to_anki(session, cloze_config)

    csv_path = tmp_path / "anki_import_cloze.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        # Skip headers
        for line in f:
            if line.startswith("#fields:"):
                break
        reader = csv.reader(f, delimiter="\t")
        row = next(reader)

    # Check Field 3 includes base verb in parentheses when show_base_verb is True
    assert (
        row[2] == "To write, think of pen and paper - regular (escribir), yo, presente"
    )


def test_cloze_export_non_verb_no_tense_info(cloze_config, tmp_path):
    """Test export of non-verb cloze card shows no verb tense info."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    cloze_config.anki_media_path.mkdir(parents=True)

    # Create a noun card (non-verb)
    card = ClozeCard(
        word="mesa",
        guid=str(uuid.uuid4()),
        word_analysis={
            "ipa": "ˈme.sa",
            "part_of_speech": "sustantivo",
            "gender": "femenino",
            "verb_type": None,  # Not a verb
            "example_sentences": [
                {"sentence": "La mesa está limpia.", "word_form": "mesa", "tense": None}
            ],
        },
        selected_sentence="La mesa está limpia.",
        selected_word_form="mesa",
        selected_tense=None,  # Not a verb, no tense
        image_path="mesa-test789.jpg",
        audio_path="mesa-test789.mp3",
        memory_aid="Table where we eat",
    )
    card.mark_complete()

    # Create mock media files
    image_path = tmp_path / card.image_path
    audio_path = tmp_path / card.audio_path
    image_path.write_text("fake image")
    audio_path.write_text("fake audio")

    session = Session(
        vocabulary_cards=[],
        cloze_cards=[card],
        output_directory=tmp_path,
    )

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"mesa_image": True, "mesa_audio": True}
        export_cloze_cards_to_anki(session, cloze_config)

    csv_path = tmp_path / "anki_import_cloze.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        # Skip headers
        for line in f:
            if line.startswith("#fields:"):
                break
        reader = csv.reader(f, delimiter="\t")
        row = next(reader)

    # Check Field 3 has only user definition (no verb info)
    assert row[2] == "Table where we eat"
