# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FluentPy is a Spanish language learning tool that helps users with pronunciation and visual memory. It uses OpenAI's APIs to generate IPA pronunciations and educational images for Spanish words, and ElevenLabs' API to generate native-speaker audio pronunciations using Mexican Spanish voices. All content is displayed directly in the terminal.

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
uv run pytest tests/test_pronunciation.py

# Run a single test
uv run pytest tests/test_pronunciation.py::test_get_pronunciation
```

### Linting and Type Checking
```bash
# Run ruff linter
ruff check .
ruff format .

# Run pyright type checker
pyright
```

**Important**: Both ruff and pyright must pass before any changes are considered complete. If these tools are not available in the environment, they should be installed and any issues fixed.

## Architecture Overview

The codebase follows a modular architecture with clear separation of concerns:

1. **`main.py`**: Entry point and orchestration layer
   - Handles user interaction via questionary prompts
   - Coordinates async execution of pronunciation and image generation using `asyncio.gather()`
   - Uses loguru for structured logging

2. **`pronunciation.py`**: IPA pronunciation generation
   - Uses OpenAI's GPT-4o model with custom Spanish pronunciation instructions
   - Returns syllable-separated IPA notation with stress markers

3. **`images.py`**: Image generation and display
   - `generate_image()`: Creates educational images using DALL-E 3
   - `view_image()`: Displays images in terminal using term-image
   - Handles base64 encoding and file operations

4. **`audio.py`**: Audio generation for pronunciation
   - `generate_audio()`: Creates audio pronunciations using ElevenLabs API
   - `get_mexican_spanish_voices()`: Filters and selects Mexican Spanish voices
   - Saves audio as MP3 files with high-quality output format

### Key Patterns

- **Async/Await**: All API calls use async patterns for concurrent execution
- **Dependency Injection**: OpenAI client objects are passed to functions rather than created internally
- **Mock-Heavy Testing**: Tests use mocks extensively to avoid API calls and ensure fast execution
- **Error Handling**: Try-catch blocks around image generation with fallback behavior
- **Type Hints**: All functions use type annotations for parameters and return values

### Testing Strategy

Tests are located in `tests/` and mirror the module structure. Key testing approaches:
- Use `pytest.mark.asyncio` for async function tests
- Mock OpenAI API calls to avoid costs and external dependencies
- Use temporary directories for file operation tests
- Verify both successful paths and error conditions

## Important Notes

- Python 3.13+ is required (specified in `.python-version`)
- The project uses UV as the package manager
- All dependencies are locked in `uv.lock`
- **All code must have type hints and pass both ruff and pyright checks**
- When making changes, always run tests, ruff, and pyright to ensure code quality