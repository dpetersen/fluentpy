import base64
from pathlib import Path

from loguru import logger
from openai import AsyncOpenAI


def get_mnemonic_filename(word: str) -> str:
    """Convert word/phrase to mnemonic filename."""
    clean_word = word.lower().replace(" ", "_")
    return f"mpi-{clean_word}.jpg"


def check_mnemonic_exists(word: str, anki_media_path: Path) -> bool:
    """Check if a mnemonic priming image already exists for a word."""
    filename = get_mnemonic_filename(word)
    path = anki_media_path / filename
    exists = path.exists()
    logger.debug("Checking mnemonic image", word=word, filename=filename, exists=exists)
    return exists


def _create_mnemonic_prompt(word: str, description: str) -> str:
    """Create a prompt for generating a mnemonic priming image."""
    prompt = f"""
    Create a memorable image that helps recall the Spanish word '{word}' through 
    phonetic similarity or sound association. The image should NOT contain any text 
    or words.
    
    Focus on creating a visual that sounds similar to '{word}' or its parts, helping 
    memory through sound association rather than meaning.
    
    User's description for phonetic association: {description}
    
    Make the image clear, memorable, and directly related to the phonetic description 
    provided. The style should be photorealistic or illustrative, whichever best 
    serves the mnemonic purpose.
    """
    return prompt.strip()


async def generate_mnemonic_image(
    *,
    client: AsyncOpenAI,
    word: str,
    description: str,
    output_path: Path,
) -> Path:
    """Generate a mnemonic priming image based on phonetic description."""
    logger.info(
        "Generating mnemonic image", word=word, description=description[:50] + "..."
    )

    prompt = _create_mnemonic_prompt(word, description)

    try:
        response = await client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="medium",
            output_format="jpeg",
            output_compression=80,
        )
        logger.debug("Received mnemonic image response", word=word)
    except Exception as e:
        logger.error(
            "Failed to generate mnemonic image",
            word=word,
            error=str(e),
        )
        raise

    if response.data:
        image_data = base64.b64decode(response.data[0].b64_json or "")

        logger.info("Writing mnemonic image", word=word, path=output_path)
        with open(output_path, "wb") as f:
            f.write(image_data)
        return output_path
    else:
        raise RuntimeError(f"No image data received for mnemonic image: {word}")
