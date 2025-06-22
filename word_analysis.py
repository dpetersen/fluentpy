import json
from typing import TypedDict

from loguru import logger
from openai import AsyncOpenAI

MODEL = "gpt-4o"
INSTRUCTIONS = "You are an expert in the Spanish language, teaching me to learn it."
INPUT_TEMPLATE = """
Analyze the Spanish word '{word}' and provide the following information in JSON format:

1. IPA pronunciation (broken down by syllable using dots (.) for syllable boundaries and ˈ to indicate primary stress)
2. Part of speech (one of: noun, verb, adjective, adverb, pronoun, preposition, conjunction, article, interjection)
3. Gender (for nouns only: masculine or feminine, otherwise null)
4. Verb type (for verbs only: transitive, intransitive, reflexive, or pronominal, otherwise null)

Return ONLY valid JSON with this structure (no markdown formatting, no code blocks):
{{
  "ipa": "string",
  "part_of_speech": "string",
  "gender": "string or null",
  "verb_type": "string or null"
}}
"""


class WordAnalysis(TypedDict):
    ipa: str
    part_of_speech: str
    gender: str | None
    verb_type: str | None


async def analyze_word(*, client: AsyncOpenAI, word: str) -> WordAnalysis:
    logger.debug("Analyzing word", word=word)
    response = await client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=INPUT_TEMPLATE.format(word=word),
    )
    logger.debug("Analysis received", word=word, response=response.output_text)

    try:
        analysis_data = json.loads(response.output_text)
        return WordAnalysis(
            ipa=analysis_data["ipa"],
            part_of_speech=analysis_data["part_of_speech"],
            gender=analysis_data.get("gender"),
            verb_type=analysis_data.get("verb_type"),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse analysis response", word=word, error=str(e))
        raise ValueError(f"Invalid response format from OpenAI: {response.output_text}")
