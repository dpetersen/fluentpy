import base64

from loguru import logger
from openai import AsyncOpenAI
from term_image.image import from_file

from word_analysis import WordAnalysis


def _create_prompt(word: str, analysis: WordAnalysis) -> str:
    base_prompt = """
    I am making memorable Anki flashcards for Spanish vocabulary. It is absolutely 
    critical that the word I give you, or any similar words, SHOULD NOT appear in 
    the image. I am looking for imagery, not traditional flash cards. The style of 
    the image can be whatever style you think best fits the word.
    
    I'm learning Latin American Spanish, Mexican specifically, so keep that in mind 
    when trying to translate the terms to images.
    """

    part_of_speech = analysis["part_of_speech"]
    gender = analysis.get("gender")

    match part_of_speech:
        case "verb":
            specific_prompt = """
            Since this is a verb, make sure there is clear action happening in the image. 
            The action should be prominent and obvious to help reinforce the verb meaning.
            """
        case "adjective":
            specific_prompt = """
            Since this is an adjective, show multiple different objects that all share 
            this adjective quality. For example, if the word means 'blue', show blue hair, 
            a blue car, and a blue bike. This helps make it clear that the adjective is 
            the focus, not any specific noun.
            """
        case "noun":
            match gender:
                case "masculine":
                    specific_prompt = """
                    I use the mnemonic that masculine words are intensely hot and fiery. 
                    Incorporate blazing flames, intense heat, burning, or fiery imagery into the scene.
                    Make it dramatically hot and fiery.
                    """
                case "feminine":
                    specific_prompt = """
                    I use the mnemonic that feminine words are intensely cold and freezing. 
                    Incorporate freezing ice, bitter cold, frost, blizzards, or arctic imagery into the scene.
                    Make it dramatically cold and freezing.
                    """
                case _:
                    specific_prompt = """
                    Create a clear, memorable image that represents this concept.
                    """
        case _:
            specific_prompt = """
            Create a clear, memorable image that represents this concept.
            """

    return f"{base_prompt.strip()}\n\n{specific_prompt.strip()}\n\nThe word is: {word}"


async def generate_image(
    *, client: AsyncOpenAI, word: str, analysis: WordAnalysis, path: str
) -> str:
    logger.debug("Generating image", word=word)
    prompt = _create_prompt(word, analysis)
    response = await client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="medium",
        output_format="jpeg",
        output_compression=80,
    )
    logger.debug("Received image response", word=word)

    if response.data:
        image_data = base64.b64decode(response.data[0].b64_json or "")

        logger.info("Writing file", word=word, path=path)
        with open(file=path, mode="wb") as f:
            f.write(image_data)
        return path
    else:
        raise RuntimeError("No image data received from API")


def view_image(path: str):
    image = from_file(path)
    image.draw()
