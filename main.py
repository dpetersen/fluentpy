import questionary
from openai import OpenAI
from pronunciation import get_pronunciation
from images import generate_image, view_image


def main():
    # Will automatically use OPENAI_API_KEY environment variable
    client = OpenAI()

    word = questionary.text(message="What is the word?").ask()
    prounciation = get_pronunciation(client=client, word=word)
    print(f"The IPA pronunciation of '{word}' is: {prounciation}")

    should_generate_image = questionary.confirm(
        message=f"Would you like to generate an image for '{word}'?", default=True
    ).ask()

    if should_generate_image:
        print(f"Generating image for '{word}'...")
        try:
            # FIXME: correct the path
            image_path = f"./{word}.png"
            generate_image(client=client, word=word, path=image_path)
            print(f"Image saved to: {image_path}")
            view_image(path=image_path)
        except Exception as e:
            print(f"Error generating image: {e}")


if __name__ == "__main__":
    main()
