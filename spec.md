# FluentPy System Specification

## Overview
FluentPy is a Spanish language learning tool that generates Anki flashcards with pronunciation audio, IPA notation, and memorable images. The system processes multiple Spanish words, generates educational media for each, allows review and regeneration, and exports everything in Anki-compatible format.

## Core Features

### 1. Batch Word Input with Metadata
- Accept multiple Spanish words in a single session
- For each word, optionally collect:
  - **Personal Context**: User-specific memory aids or usage examples
  - **Extra Image Prompt**: Additional context for more personalized image generation
- Store all word data in a session for processing

### 2. Media Generation
- **IPA Pronunciation**: Generate syllable-separated IPA with stress markers using OpenAI
- **Audio**: Generate native Mexican Spanish pronunciation using ElevenLabs
- **Images**: Create memorable visual representations using DALL-E 3
  - Verbs: Show clear action
  - Adjectives: Multiple objects sharing the quality
  - Masculine nouns: Incorporate fire/heat imagery
  - Feminine nouns: Incorporate ice/cold imagery

### 3. Review and Regeneration
- Display generated media for each word in terminal
- Allow users to:
  - Approve media for a word
  - Regenerate image with additional prompt context
  - Regenerate audio (selecting different voice if desired)
- Track satisfaction state for each word

### 4. Anki Export
- Generate CSV file with proper formatting:
  - UTF-8 encoding
  - Columns: Word, IPA, Personal Context, Image, Audio
  - Media references: `<img src="filename.jpg">` and `[sound:filename.mp3]`
- Copy all media files to Anki's collection.media folder
- Support for bulk import of multiple cards

## Data Models

### WordInput
```python
class WordInput:
    word: str
    personal_context: Optional[str]
    extra_image_prompt: Optional[str]
```

### WordCard
```python
class WordCard:
    word: str
    ipa: str
    part_of_speech: str
    gender: Optional[str]
    verb_type: Optional[str]
    personal_context: Optional[str]
    extra_image_prompt: Optional[str]
    image_path: Optional[str]
    audio_path: Optional[str]
    is_complete: bool
```

### Session
```python
class Session:
    cards: List[WordCard]
    output_directory: str
    anki_media_path: Optional[str]
```

## File Organization

```
fluentpy/
├── main.py              # Entry point and orchestration
├── models.py            # Data structures
├── word_input.py        # Batch input interface
├── word_analysis.py     # IPA and grammatical analysis (existing)
├── audio.py             # Audio generation (existing)
├── images.py            # Image generation (existing)
├── session.py           # Session state management
├── review.py            # Interactive review interface
├── anki_export.py       # CSV generation and media export
├── config.py            # Configuration and paths
└── tests/               # Test files for each module
```

## Workflow

1. **Input Phase**
   - User provides list of Spanish words
   - For each word, optionally add personal context and image hints
   - Create session with all word inputs

2. **Generation Phase**
   - For each word:
     - Analyze grammatical properties and IPA
     - Generate image (with extra prompt if provided)
     - Generate audio pronunciation
   - Save all media to session directory

3. **Review Phase**
   - Display each word with its generated media
   - User can:
     - Approve and move to next
     - Regenerate image with refined prompt
     - Regenerate audio with different voice
   - Continue until all words are approved

4. **Export Phase**
   - Generate Anki-compatible CSV
   - Copy media files to collection.media
   - Provide import instructions

## Technical Requirements

### API Integration
- OpenAI API for IPA generation and images
- ElevenLabs API for audio generation
- Proper error handling and retry logic

### File Management
- Unique filenames to avoid conflicts
- Temporary session directory for work in progress
- Clean media file names for Anki compatibility

### User Interface
- Terminal-based using questionary for prompts
- Image display using term-image
- Clear progress indicators for batch operations

### Configuration
- Anki collection path (auto-detect or manual)
- Default image generation settings
- Voice preferences for audio

## Error Handling
- API failures: Retry with exponential backoff
- File operations: Validate paths and permissions
- User interruption: Save session state for resume

## Future Enhancements
- Session save/resume for large batches
- Template customization for different card types
- Integration with Anki API for direct import
- Support for phrases and example sentences