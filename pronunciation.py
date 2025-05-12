from loguru import logger
from openai import AsyncOpenAI

MODEL = "gpt-4o"
INSTRUCTIONS = "You are an expert in the Spanish language, teaching me to learn it."
INPUT_TEMPLATE = """
Give me only the IPA pronunciation for the Spanish word '{word}', broken down by 
syllable using dots (.) for syllable boundaries and ˈ to indicate primary stress.
Return only the IPA string, no additional text.
"""


async def get_pronunciation(*, client: AsyncOpenAI, word: str) -> str:
    logger.debug("Getting pronunciation", word=word)
    response = await client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=INPUT_TEMPLATE.format(word=word),
    )
    logger.debug("Pronunciation received", word=word)
    return response.output_text
