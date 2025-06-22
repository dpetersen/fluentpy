import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from anki_export import (
    copy_media_files,
    create_csv_row,
    create_field_3_content,
    export_to_anki,
    generate_csv,
)
from config import AnkiConfig
from models import Session, WordCard


class TestCreateField3Content:
    def test_noun_with_gender_and_context(self):
        """Test field 3 content for noun with gender and personal context."""
        config = AnkiConfig()
        card = WordCard(
            word="casa",
            ipa="ˈka.sa",
            part_of_speech="noun",
            gender="feminine",
            personal_context="Mi hogar de la infancia"
        )
        
        result = create_field_3_content(card, config)
        assert result == "Sustantivo femenino. Mi hogar de la infancia."

    def test_verb_with_type(self):
        """Test field 3 content for verb with type."""
        config = AnkiConfig()
        card = WordCard(
            word="correr",
            ipa="ko.ˈrer",
            part_of_speech="verb",
            verb_type="intransitive",
            personal_context="Corro cada mañana"
        )
        
        result = create_field_3_content(card, config)
        assert result == "Verbo intransitivo. Corro cada mañana."

    def test_adjective_without_context(self):
        """Test field 3 content for adjective without personal context."""
        config = AnkiConfig()
        card = WordCard(
            word="azul",
            ipa="a.ˈsul",
            part_of_speech="adjective"
        )
        
        result = create_field_3_content(card, config)
        assert result == "Adjetivo."

    def test_interjection_with_context(self):
        """Test field 3 content for interjection with context."""
        config = AnkiConfig()
        card = WordCard(
            word="hola",
            ipa="ˈo.la",
            part_of_speech="interjection",
            personal_context="Saludo común"
        )
        
        result = create_field_3_content(card, config)
        assert result == "Interjección. Saludo común."


class TestCreateCsvRow:
    def test_complete_card_row(self):
        """Test CSV row creation for card with all media."""
        config = AnkiConfig()
        card = WordCard(
            word="gato",
            ipa="ˈga.to",
            part_of_speech="noun",
            gender="masculine",
            personal_context="Mi mascota",
            guid="test-guid-1234"
        )
        # Mock file paths
        card.image_path = Path("gato.jpg")
        card.audio_path = Path("gato.mp3")
        
        result = create_csv_row(card, config)
        
        expected = [
            "gato",
            '<img src="gato-test-gui.jpg">',
            "Sustantivo masculino. Mi mascota.",
            "[sound:gato-test-gui.mp3] ˈga.to",
            "",
            "test-guid-1234"
        ]
        assert result == expected

    def test_card_without_media(self):
        """Test CSV row for card without image or audio."""
        config = AnkiConfig()
        card = WordCard(
            word="palabra",
            ipa="pa.ˈla.βra",
            part_of_speech="noun",
            gender="feminine",
            guid="test-guid-5678"
        )
        
        result = create_csv_row(card, config)
        
        expected = [
            "palabra",
            "",
            "Sustantivo femenino.",
            "pa.ˈla.βra",
            "",
            "test-guid-5678"
        ]
        assert result == expected

    def test_card_with_test_spelling_enabled(self):
        """Test CSV row with test spelling enabled."""
        config = AnkiConfig(test_spelling=True)
        card = WordCard(
            word="escribir",
            ipa="es.kri.ˈβir",
            part_of_speech="verb",
            guid="test-guid-9999"
        )
        
        result = create_csv_row(card, config)
        
        assert result[4] == "y"  # Test spelling field should be "y"


class TestCopyMediaFiles:
    def test_copies_media_successfully(self):
        """Test successful media file copying."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up source files
            session_dir = Path(tmpdir) / "session"
            session_dir.mkdir()
            anki_dir = Path(tmpdir) / "anki"
            anki_dir.mkdir()
            
            # Create test files
            image_file = session_dir / "casa-12345678.jpg"
            audio_file = session_dir / "casa-12345678.mp3"
            image_file.write_text("fake image")
            audio_file.write_text("fake audio")
            
            # Set up session and card
            session = Session(output_directory=session_dir)
            card = WordCard(
                word="casa",
                ipa="ˈka.sa",
                part_of_speech="noun",
                guid="12345678-1234-5678-9abc-def012345678",
                image_path=image_file,
                audio_path=audio_file
            )
            card.mark_complete()
            session.add_card(card)
            
            config = AnkiConfig(anki_media_path=anki_dir)
            
            result = copy_media_files(session, config)
            
            # Check results
            assert result["casa_image"] is True
            assert result["casa_audio"] is True
            
            # Check files were copied
            assert (anki_dir / "casa-12345678.jpg").exists()
            assert (anki_dir / "casa-12345678.mp3").exists()

    @patch("config.find_anki_collection_media")
    def test_raises_error_for_missing_anki_path(self, mock_find):
        """Test error when Anki media path not found."""
        mock_find.return_value = None  # Simulate not finding Anki path
        
        session = Session()
        config = AnkiConfig(anki_media_path=None)
        
        with pytest.raises(ValueError, match="Anki collection.media path not found"):
            copy_media_files(session, config)

    def test_skips_incomplete_cards(self):
        """Test that incomplete cards are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            anki_dir = Path(tmpdir)
            session = Session()
            
            # Add incomplete card
            card = WordCard(word="test", ipa="test", part_of_speech="noun")
            # Don't mark as complete
            session.add_card(card)
            
            config = AnkiConfig(anki_media_path=anki_dir)
            
            result = copy_media_files(session, config)
            
            # Should return empty results (no files copied)
            assert len(result) == 0


class TestGenerateCsv:
    def test_generates_csv_successfully(self):
        """Test successful CSV generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            
            session = Session()
            card = WordCard(
                word="perro",
                ipa="ˈpe.ro", 
                part_of_speech="noun",
                gender="masculine",
                guid="test-guid-abcd"
            )
            card.mark_complete()
            session.add_card(card)
            
            config = AnkiConfig()
            
            result = generate_csv(session, config, output_path)
            
            assert result is True
            assert output_path.exists()
            
            # Check CSV content
            content = output_path.read_text()
            assert "#notetype:2. Picture Words" in content
            assert "#deck:FluentPy Test" in content
            assert "perro" in content

    def test_fails_for_incomplete_session(self):
        """Test CSV generation fails for incomplete session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            
            session = Session()
            card = WordCard(word="test", ipa="test", part_of_speech="noun")
            # Don't mark as complete
            session.add_card(card)
            
            config = AnkiConfig()
            
            result = generate_csv(session, config, output_path)
            
            assert result is False
            assert not output_path.exists()


class TestExportToAnki:
    @patch("anki_export.copy_media_files")
    @patch("anki_export.generate_csv")
    def test_successful_export(self, mock_generate_csv, mock_copy_media):
        """Test complete successful export process."""
        # Mock successful operations
        mock_copy_media.return_value = {"test_image": True}
        mock_generate_csv.return_value = True
        
        session = Session()
        card = WordCard(word="test", ipa="test", part_of_speech="noun")
        card.mark_complete()
        session.add_card(card)
        
        result = export_to_anki(session)
        
        assert result is True
        mock_copy_media.assert_called_once()
        mock_generate_csv.assert_called_once()

    def test_fails_for_incomplete_session(self):
        """Test export fails for incomplete session."""
        session = Session()
        card = WordCard(word="test", ipa="test", part_of_speech="noun")
        # Don't mark as complete
        session.add_card(card)
        
        result = export_to_anki(session)
        
        assert result is False