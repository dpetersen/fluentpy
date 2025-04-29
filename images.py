import base64

from openai import OpenAI
from term_image.image import from_file


def generate_image(*, client: OpenAI, word: str, path: str):
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"Create a clear, educational image representing the Spanish word '{word}'. The image should help language learners remember the meaning.",
        n=1,
        size="1024x1024",
        response_format="b64_json",
    )

    if response.data:
        image_data = base64.b64decode(response.data[0].b64_json or "")

        with open(file=path, mode="wb") as f:
            f.write(image_data)


def view_image(path: str):
    image = from_file(path)
    image.draw()
