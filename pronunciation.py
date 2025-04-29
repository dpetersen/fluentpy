from openai import OpenAI

MODEL = "gpt-4o"
INSTRUCTIONS = "You are an expert in the Spanish language, teaching me to learn it."
INPUT_TEMPLATE = """
Give me only the IPA pronunciation for the Spanish word '{word}', broken down by 
syllable using dots (.) for syllable boundaries and ˈ to indicate primary stress.
Return only the IPA string, no additional text.
"""


def get_pronunciation(*, client: OpenAI, word: str) -> str:
    response = client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=INPUT_TEMPLATE.format(word=word),
    )
    return response.output_text
