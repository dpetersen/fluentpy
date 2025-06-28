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
  "verb_type": "string or null",
  "example_sentences": []
}}
"""

INPUT_TEMPLATE_WITH_EXAMPLES = """
Analyze the Spanish word '{word}' and provide the following information in JSON format:

1. IPA pronunciation (broken down by syllable using dots (.) for syllable boundaries and ˈ to indicate primary stress)
2. Part of speech (one of: noun, verb, adjective, adverb, pronoun, preposition, conjunction, article, interjection)
3. Gender (for nouns only: masculine or feminine, otherwise null)
4. Verb type (for verbs only: transitive, intransitive, reflexive, or pronominal, otherwise null)
Additionally, provide exactly 15 example sentences that demonstrate the word '{word}' in context. Requirements:
- Each sentence MUST include the exact word '{word}' or its conjugated/inflected forms
- Use beginner to intermediate vocabulary to keep focus on the target word
- Use idiomatic Mexican Spanish expressions and phrasing
- For verbs: include variety of conjugations (yo, tú, él/ella, nosotros, etc.) AND various tenses (present, preterite, imperfect, future, conditional, present subjunctive) plus at least one infinitive usage (e.g., "puedo hablar")
- Keep sentences practical and conversational
- Each sentence should be 6-12 words long for clarity
- CRITICAL: For each sentence, the "word_form" field must contain the EXACT form of the word that appears in the sentence text. The sentence text must contain this exact word_form identically - character for character, case for case.
- For each sentence, include the "ipa" field with the IPA pronunciation of the specific word_form used in that sentence (NOT the base word's IPA)
- For verbs, include the "tense" field with the grammatical tense in Spanish (e.g., "presente", "pretérito", "imperfecto", "futuro", "condicional", "presente de subjuntivo", "imperativo", etc.)
- For non-verbs, the "tense" field should be null

Return ONLY valid JSON with this structure (no markdown formatting, no code blocks):
{{
  "ipa": "string",
  "part_of_speech": "string",
  "gender": "string or null",
  "verb_type": "string or null",
  "example_sentences": [
    {{"sentence": "sentence text", "word_form": "exact conjugated form in sentence", "ipa": "IPA of word_form", "tense": "tense name or null"}},
    {{"sentence": "sentence text", "word_form": "exact conjugated form in sentence", "ipa": "IPA of word_form", "tense": "tense name or null"}}
  ]
}}
"""


class ExampleSentence(TypedDict):
    sentence: str
    word_form: str
    ipa: str
    tense: str | None


class WordAnalysis(TypedDict):
    ipa: str
    part_of_speech: str
    gender: str | None
    verb_type: str | None
    example_sentences: list[ExampleSentence]


async def analyze_word(
    *, client: AsyncOpenAI, word: str, request_examples: bool = False
) -> WordAnalysis:
    logger.debug("Analyzing word", word=word, request_examples=request_examples)

    template = INPUT_TEMPLATE_WITH_EXAMPLES if request_examples else INPUT_TEMPLATE

    response = await client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=template.format(word=word),
    )
    logger.debug("Analysis received", word=word, response=response.output_text)

    try:
        analysis_data = json.loads(response.output_text)
        return WordAnalysis(
            ipa=analysis_data["ipa"],
            part_of_speech=analysis_data["part_of_speech"],
            gender=analysis_data.get("gender"),
            verb_type=analysis_data.get("verb_type"),
            example_sentences=analysis_data.get("example_sentences", []),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse analysis response", word=word, error=str(e))
        raise ValueError(f"Invalid response format from OpenAI: {response.output_text}")
