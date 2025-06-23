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
                "La casa es muy grande.",
                "Vivo en una casa blanca.",
                "Mi casa tiene jardín.",
            ],
        },
        selected_sentence="La casa es muy grande.",
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
    assert "La ______ es muy grande." in content  # Cloze export uses ______ not {{c1::}}

    # Verify media copying was called
    assert mock_copy.call_count == 1


def test_export_cloze_cards_csv_headers(session_with_cloze_cards, cloze_config, tmp_path):
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
    ]
    expected_header = "#fields:" + "\t".join(expected_fields)
    assert fields_line == expected_header


def test_export_cloze_cards_csv_content(session_with_cloze_cards, cloze_config, tmp_path):
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
    assert row[2] == "Think of your childhood home"  # Front (Definitions) - only memory_aid, no word
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


def test_export_cloze_cards_missing_media_files(session_with_cloze_cards, cloze_config, tmp_path):
    """Test export handling of missing media files."""
    cloze_config.anki_media_path = tmp_path / "collection_media"
    session_with_cloze_cards.output_directory = tmp_path

    cloze_config.anki_media_path.mkdir(parents=True)
    
    # Don't create media files to simulate missing files
    # But mark the card as complete
    card = session_with_cloze_cards.cloze_cards[0]
    card.mark_complete()

    with patch("cloze_export.copy_cloze_media_files") as mock_copy:
        mock_copy.return_value = {"casa_image": False, "casa_audio": False}  # Simulate copy failure but return dict
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
                "example_sentences": [f"Sentence with {word}."],
            },
            selected_sentence=f"Sentence with {word}.",
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
        mock_copy.return_value = {"casa_image": True, "casa_audio": True, "perro_image": True, "perro_audio": True, "libro_image": True, "libro_audio": True}
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


def test_export_cloze_cards_error_handling(session_with_cloze_cards, cloze_config, tmp_path):
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