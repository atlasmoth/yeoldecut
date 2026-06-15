from dotenv import load_dotenv

load_dotenv()

from director.engine import run_model
from audio.engine import generate_voice
from images.engine import generate_images
from sound.engine import generate_sound


breakup_text = """I’m done. Not “let’s take a break,” not “maybe someday,” done.

I gave you patience, chances, explanations, and more grace than you deserved. You gave me excuses, inconsistency, and the exhausting job of trying to love someone who only showed up when it was convenient.

I don’t hate you, but I am embarrassed by how long I let you convince me that crumbs were effort. I deserve honesty, respect, and peace — and you have made it painfully clear that none of those are things you’re capable of giving me.

Please don’t call, don’t text, and don’t try to rewrite this into some misunderstanding. It isn’t. This is me finally choosing myself."""

def main():
    result = run_model(
        rejection_text=breakup_text,
    )

    image_prompts = [
        f"{scene.get('image_prompt', '')} Negative prompt: {scene.get('negative_prompt', '')}"
        for scene in result.get("scenes", [])
    ]
    transcript = result.get("narration").get("full_script")
    music = result.get("narration").get("music")

    generate_sound(music)
    generate_voice(transcript)
    generate_images(image_prompts)


if __name__ == "__main__":
    main()
