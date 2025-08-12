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
from models import Session, WordCard, ClozeCard


class TestCreateField3Content:
    def test_noun_with_gender_and_context(self):
        """Test field 3 content for noun with gender and personal context."""
        config = AnkiConfig()
        card = WordCard(
            word="casa",
            ipa="ˈka.sa",
            part_of_speech="noun",
            gender="feminine",
            personal_context="Mi hogar de la infancia",
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
            personal_context="Corro cada mañana",
        )

        result = create_field_3_content(card, config)
        assert result == "Verbo intransitivo. Corro cada mañana."

    def test_adjective_without_context(self):
        """Test field 3 content for adjective without personal context."""
        config = AnkiConfig()
        card = WordCard(word="azul", ipa="a.ˈsul", part_of_speech="adjective")

        result = create_field_3_content(card, config)
        assert result == "Adjetivo."

    def test_interjection_with_context(self):
        """Test field 3 content for interjection with context."""
        config = AnkiConfig()
        card = WordCard(
            word="hola",
            ipa="ˈo.la",
            part_of_speech="interjection",
            personal_context="Saludo común",
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
            guid="test-guid-1234",
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
            "test-guid-1234",
            "",  # No mnemonic image
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
            guid="test-guid-5678",
        )

        result = create_csv_row(card, config)

        expected = [
            "palabra",
            "",
            "Sustantivo femenino.",
            "pa.ˈla.βra",
            "",
            "test-guid-5678",
            "",  # No mnemonic image
        ]
        assert result == expected

    def test_card_with_test_spelling_enabled(self):
        """Test CSV row with test spelling enabled."""
        config = AnkiConfig(test_spelling=True)
        card = WordCard(
            word="escribir",
            ipa="es.kri.ˈβir",
            part_of_speech="verb",
            guid="test-guid-9999",
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
                audio_path=audio_file,
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

    def test_only_copies_vocabulary_card_media(self):
        """Test that copy_media_files only copies vocabulary card media, not cloze."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            anki_dir = Path(tmpdir) / "anki"
            anki_dir.mkdir()

            session = Session(output_directory=output_dir)

            # Create vocabulary card with media
            vocab_card = WordCard(
                word="gato",
                ipa="ˈga.to",
                part_of_speech="noun",
                gender="masculine",
                guid="vocab-guid-9999",
            )
            vocab_image = output_dir / "gato-vocab-gui.jpg"
            vocab_audio = output_dir / "gato-vocab-gui.mp3"
            vocab_image.write_text("vocab image")
            vocab_audio.write_text("vocab audio")
            vocab_card.image_path = vocab_image
            vocab_card.audio_path = vocab_audio
            vocab_card.mark_complete()
            session.add_card(vocab_card)

            # Create cloze card with media
            cloze_card = ClozeCard(
                word="comer",
                word_analysis={
                    "ipa": "koˈmeɾ",
                    "part_of_speech": "verb",
                    "verb_type": "er_verb",
                    "gender": None,
                    "example_sentences": [],
                },
                selected_sentence="Yo como pan",
                selected_word_form="como",
                selected_word_ipa="ˈko.mo",
                guid="cloze-guid-8888",
            )
            cloze_image = output_dir / "comer-cloze-gui.jpg"
            cloze_audio = output_dir / "comer-cloze-gui.mp3"
            cloze_image.write_text("cloze image")
            cloze_audio.write_text("cloze audio")
            cloze_card.image_path = cloze_image
            cloze_card.audio_path = cloze_audio
            cloze_card.mark_complete()
            session.add_card(cloze_card)

            config = AnkiConfig(anki_media_path=anki_dir)
            result = copy_media_files(session, config)

            # Should only copy vocabulary card media
            assert len(result) == 2  # vocab image and audio
            assert "gato_image" in result
            assert "gato_audio" in result
            assert result["gato_image"] is True
            assert result["gato_audio"] is True

            # Cloze media should NOT be copied
            assert "comer_image" not in result
            assert "comer_audio" not in result

            # Check actual files in anki directory
            anki_files = list(anki_dir.glob("*"))
            assert len(anki_files) == 2
            vocab_files = [f.name for f in anki_files]
            assert any("gato" in f and ".jpg" in f for f in vocab_files)
            assert any("gato" in f and ".mp3" in f for f in vocab_files)
            assert not any("comer" in f for f in vocab_files)


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
                guid="test-guid-abcd",
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
            assert "#deck:Fluent Forever Spanish::2. Everything Else" in content
            assert "#fields:Word\tPicture\t" in content  # Verify proper field headers
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

    def test_only_exports_vocabulary_cards(self):
        """Test that export only includes vocabulary cards, not cloze cards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"

            session = Session()

            # Add a vocabulary card
            vocab_card = WordCard(
                word="casa",
                ipa="ˈka.sa",
                part_of_speech="noun",
                gender="feminine",
                guid="vocab-guid-1234",
            )
            vocab_card.mark_complete()
            session.add_card(vocab_card)

            # Add a cloze card
            cloze_card = ClozeCard(
                word="hablar",
                word_analysis={
                    "ipa": "aˈβlaɾ",
                    "part_of_speech": "verb",
                    "verb_type": "ar_verb",
                    "gender": None,
                    "example_sentences": [],
                },
                selected_sentence="Yo hablo español",
                selected_word_form="hablo",
                selected_word_ipa="ˈa.βlo",
                guid="cloze-guid-5678",
            )
            cloze_card.mark_complete()
            session.add_card(cloze_card)

            config = AnkiConfig()
            result = generate_csv(session, config, output_path)

            assert result is True
            assert output_path.exists()

            # Check CSV content only has vocabulary card
            content = output_path.read_text()
            assert "casa" in content
            assert "vocab-guid-1234" in content

            # Cloze card should NOT be in the output
            assert "hablar" not in content
            assert "hablo" not in content
            assert "cloze-guid-5678" not in content
            assert "Yo hablo español" not in content


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
