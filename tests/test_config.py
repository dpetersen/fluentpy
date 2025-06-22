from pathlib import Path
from unittest.mock import patch

from config import AnkiConfig, find_anki_collection_media


class TestFindAnkiCollectionMedia:
    @patch("config.Path.home")
    @patch("config.Path.exists")
    @patch("config.Path.is_dir")
    def test_finds_linux_path(self, mock_is_dir, mock_exists, mock_home):
        """Test finding Anki media folder on Linux."""
        mock_home.return_value = Path("/home/user")
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        
        result = find_anki_collection_media()
        
        expected = Path("/home/user/.local/share/Anki2/User 1/collection.media")
        assert result == expected

    @patch("config.Path.home")
    @patch("config.Path.exists")
    def test_returns_none_when_not_found(self, mock_exists, mock_home):
        """Test returns None when no Anki folder found."""
        mock_home.return_value = Path("/home/user")
        mock_exists.return_value = False
        
        result = find_anki_collection_media()
        
        assert result is None


class TestAnkiConfig:
    def test_default_initialization(self):
        """Test AnkiConfig with default values."""
        config = AnkiConfig()
        
        assert config.deck_name == "FluentPy Test"
        assert config.test_spelling is False
        assert config.NOTE_TYPE == "2. Picture Words"

    def test_custom_initialization(self):
        """Test AnkiConfig with custom values."""
        custom_path = Path("/custom/path")
        config = AnkiConfig(
            deck_name="My Custom Deck",
            anki_media_path=custom_path,
            test_spelling=True
        )
        
        assert config.deck_name == "My Custom Deck"
        assert config.anki_media_path == custom_path
        assert config.test_spelling is True

    def test_get_spanish_part_of_speech(self):
        """Test Spanish part of speech translation."""
        config = AnkiConfig()
        
        assert config.get_spanish_part_of_speech("noun") == "Sustantivo"
        assert config.get_spanish_part_of_speech("verb") == "Verbo"
        assert config.get_spanish_part_of_speech("unknown") == "Unknown"

    def test_get_spanish_gender(self):
        """Test Spanish gender translation."""
        config = AnkiConfig()
        
        assert config.get_spanish_gender("masculine") == "masculino"
        assert config.get_spanish_gender("feminine") == "femenino"
        assert config.get_spanish_gender(None) == ""
        assert config.get_spanish_gender("unknown") == "unknown"

    def test_get_spanish_verb_type(self):
        """Test Spanish verb type translation."""
        config = AnkiConfig()
        
        assert config.get_spanish_verb_type("transitive") == "transitivo"
        assert config.get_spanish_verb_type("reflexive") == "reflexivo"
        assert config.get_spanish_verb_type(None) == ""
        assert config.get_spanish_verb_type("unknown") == "unknown"