# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FluentPy is a Spanish language learning tool that generates Anki flashcards with pronunciation audio, IPA notation, and memorable images. The system processes multiple Spanish words in batch sessions, generates educational media for each, allows interactive review and regeneration, and exports everything in Anki-compatible format with UUID-based collision prevention.

### Core Purpose and User Motivation

The user created this tool to solve specific problems with Spanish language learning:
1. **Memory aid through visual associations**: Uses distinctive imagery to help remember words
2. **Gender learning through mnemonics**: Masculine nouns incorporate fire/heat imagery, feminine nouns use ice/cold imagery in a surrealist style
3. **Pronunciation accuracy**: Generates native Mexican Spanish audio with IPA notation
4. **Anki integration**: Seamlessly exports to the user's existing "2. Picture Words" note type
5. **Batch processing efficiency**: Handle multiple words in one session rather than one-at-a-time workflow

### Learning Philosophy: Immersion-Based Learning
**CRITICAL**: This tool follows immersion-based learning principles. All flashcard content is in Spanish only - no English translations are used in the final cards. Learning occurs through:
- **Visual associations** (images that represent the concept)
- **Audio pronunciation** (native Mexican Spanish)
- **Context** (example sentences in Spanish)
- **Grammar patterns** (IPA, parts of speech in Spanish)

The user learns Spanish through Spanish, not through translation. This is a core tenet of the learning methodology.

## Development Commands

### Running the Application
```bash
# Requires OPENAI_API_KEY and ELEVENLABS_API_KEY environment variables
uv run python main.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_images.py

# Run a single test
uv run pytest tests/test_word_analysis.py::test_analyze_word_interjection
```

### Linting and Type Checking
```bash
# Run ruff linter and formatter via uv
uv run ruff check .
uv run ruff format .

# Run pyright type checker via uv
uv run pyright
```

**Important**: Both ruff and pyright must pass before any changes are considered complete. Always run these tools via `uv run` to ensure they use the project's environment and dependencies.

## Architecture Overview

The codebase follows a modular architecture with clear separation of concerns, implementing a complete batch processing workflow:

### Core Workflow Modules

1. **`main.py`**: Entry point and orchestration layer
   - Implements complete 5-step workflow: input → generation → review → export
   - Uses async questionary for all user interactions (critical: always use `.ask_async()` not `.ask()`)
   - Coordinates batch processing with proper error handling at each stage

2. **`word_input.py`**: Batch word collection interface
   - Interactive collection of Spanish words with optional metadata
   - Captures personal context (memory aids) and extra image prompts
   - Returns list of `WordInput` objects for session processing

3. **`models.py`**: Core data structures with UUID integration
   - `WordInput`: Raw user input with word and optional metadata
   - `WordCard`: Complete card with analysis, media paths, and UUID for collision prevention
   - `ClozeCard`: Cloze card with sentence selection support
   - `Session`: Container for cards with output directory management
   - `ClozeCard.create_duplicate_with_sentence()`: Creates new cards from additional sentence selections

4. **`session.py`**: Session state management and media generation
   - `create_session()`: Analyzes words and creates WordCard objects
   - `generate_media_for_session()`: Concurrent media generation with rate limiting (max 2 operations)
   - `regenerate_image()` / `regenerate_audio()`: Handles user-requested regeneration

5. **`review.py`**: Interactive media review system
   - Displays generated media in terminal (images via term-image)
   - Allows approval, image regeneration with additional context, audio regeneration
   - `select_sentences_for_cloze_card()`: Multi-select interface for choosing sentences
   - Supports creating multiple cloze cards from different conjugations/sentences
   - Tracks completion state until all cards approved

6. **`anki_export.py`**: CSV generation and media file management
   - Generates Anki-compatible CSV with `#fields:` header prefix (critical for proper import)
   - Copies media files to Anki's collection.media folder with UUID-based naming
   - Uses Spanish grammar terms in field formatting as requested by user

### Supporting Modules

7. **`word_analysis.py`**: Grammatical analysis and IPA generation
   - Uses OpenAI GPT-4o for Spanish word analysis (IPA, part of speech, gender, verb type)
   - Generates 15 example sentences for cloze cards with different conjugations and tenses
   - For verbs: includes present, preterite, imperfect, future, conditional, and subjunctive forms
   - Each example sentence includes tense information (e.g., "presente", "pretérito", "imperfecto")
   - Returns structured `WordAnalysis` dictionary for consistent data handling

8. **`images.py`**: Image generation with specialized prompts
   - **Critical design**: Uses distinctive imagery for gender learning:
     - Masculine nouns: "on fire, surrounded by fire, smoking heavily" (surrealist style)
     - Feminine nouns: "intensely cold, icicles" (surrealist style) 
     - Verbs: Clear action emphasis "like safety card or comic book"
     - Adjectives: Multiple objects sharing the quality
   - Incorporates user's extra image prompts as "Additional context"
   - **Important**: Always pass `extra_prompt` parameter through the call chain

9. **`audio.py`**: Mexican Spanish audio generation
   - Uses ElevenLabs API with Mexican Spanish voice filtering
   - Generates high-quality MP3 files for pronunciation

10. **`config.py`**: Configuration and Anki integration
    - Auto-detects Anki collection.media path
    - Spanish grammar term mappings (user preference over English terms)
    - Field configuration for "2. Picture Words" note type

## Key Design Decisions and User Requirements

### UUID-Based Collision Prevention
The user specifically requested UUID-based file naming to prevent collisions with existing Anki media. Each `WordCard` gets a unique GUID, and media files use format: `{word}-{short_id}.{ext}` (e.g., `casa-f3adf9cf.jpg`).

### Spanish Grammar Preference
User prefers Spanish grammar terms over English in Anki fields:
- "Sustantivo" not "Noun"
- "Verbo" not "Verb"  
- "masculino/femenino" not "masculine/feminine"

### Gender Learning Strategy
**Critical user requirement**: The distinctive imagery for noun genders is a core learning strategy:
- **Masculine**: Fire/heat imagery helps memorize masculine words
- **Feminine**: Ice/cold imagery helps memorize feminine words
- **Surrealist approach**: Effects don't impact surroundings (fire doesn't burn environment, ice doesn't freeze environment)

### Anki Integration Requirements
- Must work with existing "2. Picture Words" note type (6 fields including GUID)
- CSV format requires `#fields:` prefix for headers (learned from debugging)
- Media files copied to collection.media folder, not imported as attachments
- Uses GUID column for duplicate prevention

### Async Architecture Considerations
**Critical**: All questionary interactions must use `.ask_async()` not `.ask()` to prevent asyncio event loop conflicts. This was a major debugging issue that required updating all user interaction code.

### Multi-Card Generation for Cloze Cards
Users can select multiple sentences when creating cloze cards, particularly useful for verbs with different conjugations:
- During cloze card creation, a checkbox interface allows selecting multiple sentences
- Each selected sentence generates a separate card with unique GUID and media
- First selection updates the original card, additional selections create duplicates
- Each card gets context-specific image and audio based on its sentence

### Tense Display for Learning
To help users learn Spanish tenses, the system displays grammatical tense information:
- Sentence selection shows tense for each option (e.g., "uses: habla, tense: presente")
- Review UI displays tense in brackets (e.g., "habla (hablar) [presente]")
- Card details show tense information below the selected sentence
- Helps distinguish between pretérito/imperfecto and other challenging tense pairs

## Key Patterns

- **Async/Await**: All API calls and user interactions use async patterns
- **Rate Limiting**: Max 2 concurrent API operations to respect service limits
- **Dependency Injection**: Client objects passed to functions rather than created internally
- **Mock-Heavy Testing**: Tests use mocks extensively to avoid API calls and ensure fast execution
- **UUID Integration**: Every card gets unique identifier for collision-free media naming
- **Type Hints**: All functions use type annotations for parameters and return values

### Testing Strategy

Tests are located in `tests/` and mirror the module structure. Key testing approaches:
- Use `pytest.mark.asyncio` for async function tests
- Use `AsyncMock` for questionary and API mocks (critical for async compatibility)
- Mock OpenAI/ElevenLabs API calls to avoid costs and external dependencies
- Use temporary directories for file operation tests
- Verify both successful paths and error conditions
- Test UUID generation and media path creation

## Critical Implementation Notes

### Questionary Async Integration
**Always use `.ask_async()`** - Using `.ask()` causes "RuntimeError: asyncio.run() cannot be called from a running event loop"

### Extra Image Prompt Handling
The `extra_prompt` parameter must be passed through the entire call chain:
`word_input.py` → `models.py` → `session.py` → `images.py`

### Anki CSV Format
Headers must use `#fields:` prefix, not just field names as first row, or Anki creates fake cards from headers.

### Image Prompt Testing
When updating image prompts, corresponding test assertions need updates to match new keywords.

## Development Environment

- Python 3.13+ is required (specified in `.python-version`)
- The project uses UV as the package manager  
- All dependencies are locked in `uv.lock`
- **All code must have type hints and pass both ruff and pyright checks**
- When making changes, always run tests, ruff, and pyright to ensure code quality

### External Dependencies

- **mpv**: Required for audio playback functionality. The application checks for mpv availability at startup and will exit with installation instructions if not found.

## Limitations and Future Enhancements

### User-Requested Design
The user specifically chose a terminal interface over GUI for simplicity and speed. The batch processing workflow was designed to be efficient for their learning process.

### Desired Future Functionality

- BUG: when I do too many cloze cards, I'm seeing some have no image found. I think maybe I'm getting rate limited by OpenAI?
- Add English translation for sentences that show up in my review UI only.
- Need to get OpenAI to generate image prompts for me. I want it to try and generate an image that shows who is speaking to whom, and when they are talking about future/current/past actions?
- Create multiple images per prompt and choose one
- Allow specifying my own example sentence for cloze.
- Automatic translation of personal notes, optionally
- Periodic deck backups to S3
    - Anki does not backup media, supposedly, and this would help to make sure we don't lose anything.
