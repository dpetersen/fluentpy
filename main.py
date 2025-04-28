import questionary
from openai import OpenAI
import base64


def main():
    # Assumes OPENAI_API_KEY is set
    client = OpenAI()

    word = questionary.text(message="What is the word?").ask()
    prounciation = get_pronunciation(client=client, word=word)
    print(f"The IPA pronunciation of '{word}' is: {prounciation}")

    # Ask if user wants to generate an image
    generate_img = questionary.confirm(
        message=f"Would you like to generate an image for '{word}'?", default=True
    ).ask()

    if generate_img:
        print(f"Generating image for '{word}'...")
        try:
            image_path = generate_image(client=client, word=word)
            print(f"Image saved to: {image_path}")
        except Exception as e:
            print(f"Error generating image: {e}")


def get_pronunciation(*, client: OpenAI, word: str) -> str:
    response = client.responses.create(
        model="gpt-4o",
        instructions="You are an expert in the Spanish language, teaching me to learn it.",
        input=f"Give me only the IPA pronunciation for the Spanish word '{word}', broken down by syllable using dots (.) for syllable boundaries and ˈ to indicate primary stress. Return only the IPA string, no additional text.",
    )
    return response.output_text


def generate_image(*, client: OpenAI, word: str) -> str | None:
    # Generate image with DALL-E
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"Create a clear, educational image representing the Spanish word '{word}'. The image should help language learners remember the meaning.",
        n=1,
        size="512x512",
        response_format="b64_json",
    )

    if response.data:
        image_data = base64.b64decode(response.data[0].b64_json or "")

        with open(f"{word}.png", "wb") as f:
            f.write(image_data)

        return f"{word}.png"


if __name__ == "__main__":
    main()
