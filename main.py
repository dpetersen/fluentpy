import questionary
from openai import OpenAI


def main():
    # Assumes OPENAI_API_KEY is set
    client = OpenAI()

    word = questionary.text(message="What is the word?").ask()
    prounciation = get_pronunciation(client, word)
    print(f"The IPA pronunciation of '{word}' is: {prounciation}")


def get_pronunciation(client: OpenAI, word: str) -> str:
    response = client.responses.create(
        model="gpt-4o",
        instructions="You are an expert in the Spanish language, teaching me to learn it.",
        input=f"Give me only the IPA pronunciation for the Spanish word '{word}', broken down by syllable using dots (.) for syllable boundaries and ˈ to indicate primary stress. Return only the IPA string, no additional text.",
    )
    return response.output_text


if __name__ == "__main__":
    main()
