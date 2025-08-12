import pytest
from pathlib import Path
from anki_export import create_csv_row
from cloze_export import create_cloze_csv_row
from config import AnkiConfig, ClozeAnkiConfig
from models import WordCard, ClozeCard


class TestMnemonicExportVocabulary:
    def test_card_with_mnemonic_image(self):
        """Test CSV row includes mnemonic image when has_mnemonic_image is True."""
        config = AnkiConfig()
        card = WordCard(
            word="dormir",
            ipa="dor.ˈmir",
            part_of_speech="verb",
            guid="test-guid-1234",
            has_mnemonic_image=True,
        )

        result = create_csv_row(card, config)

        # Should have 7 fields
        assert len(result) == 7
        # Last field should have mnemonic image HTML
        assert result[6] == '<img src="mpi-dormir.jpg">'

    def test_card_without_mnemonic_image(self):
        """Test CSV row has empty mnemonic field when has_mnemonic_image is False."""
        config = AnkiConfig()
        card = WordCard(
            word="casa",
            ipa="ˈka.sa",
            part_of_speech="noun",
            guid="test-guid-5678",
            has_mnemonic_image=False,
        )

        result = create_csv_row(card, config)

        # Should have 7 fields
        assert len(result) == 7
        # Last field should be empty
        assert result[6] == ""

    def test_mnemonic_filename_normalization(self):
        """Test mnemonic filename is normalized (lowercase, underscores)."""
        config = AnkiConfig()
        card = WordCard(
            word="De Hecho",  # Phrase with capital letters and space
            ipa="de.ˈe.tʃo",
            part_of_speech="phrase",
            guid="test-guid-9999",
            has_mnemonic_image=True,
        )

        result = create_csv_row(card, config)

        # Mnemonic filename should be normalized
        assert result[6] == '<img src="mpi-de_hecho.jpg">'


class TestMnemonicExportCloze:
    def test_cloze_card_with_mnemonic_image(self):
        """Test Cloze CSV row includes mnemonic image in field 10."""
        config = ClozeAnkiConfig()
        card = ClozeCard(
            word="hablar",
            word_analysis={
                "ipa": "a.ˈβlar",
                "part_of_speech": "verb",
                "verb_type": "intransitive",
            },
            selected_sentence="Yo hablo español",
            selected_word_form="hablo",
            guid="test-guid-cloze",
            has_mnemonic_image=True,
        )
        card.mark_complete()

        result = create_cloze_csv_row(card, config)

        # Should have 10 fields
        assert len(result) == 10
        # Fields 7-9 should be empty
        assert result[6] == ""
        assert result[7] == ""
        assert result[8] == ""
        # Field 10 should have mnemonic image
        assert result[9] == '<img src="mpi-hablar.jpg">'

    def test_cloze_card_without_mnemonic_image(self):
        """Test Cloze CSV row has empty mnemonic field when has_mnemonic_image is False."""
        config = ClozeAnkiConfig()
        card = ClozeCard(
            word="comer",
            word_analysis={
                "ipa": "ko.ˈmer",
                "part_of_speech": "verb",
            },
            selected_sentence="Ella come frutas",
            selected_word_form="come",
            guid="test-guid-cloze2",
            has_mnemonic_image=False,
        )
        card.mark_complete()

        result = create_cloze_csv_row(card, config)

        # Should have 10 fields
        assert len(result) == 10
        # All empty fields should be empty
        assert result[6] == ""
        assert result[7] == ""
        assert result[8] == ""
        assert result[9] == ""  # No mnemonic image

    def test_cloze_empty_padding_fields(self):
        """Test that fields 7-9 are always empty for Cloze cards."""
        config = ClozeAnkiConfig()
        card = ClozeCard(
            word="test",
            word_analysis={"ipa": "test", "part_of_speech": "noun"},
            guid="test-guid",
            has_mnemonic_image=True,
        )

        result = create_cloze_csv_row(card, config)

        # Fields 7-9 should always be empty strings
        assert result[6] == ""
        assert result[7] == ""
        assert result[8] == ""
        # Only field 10 can have content (mnemonic image)
        assert len(result[9]) > 0  # Has mnemonic image
