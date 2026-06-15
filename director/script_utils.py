from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json



SCENE_TEMPLATES: List[str] = [
    "cold_open_parchment",
    "the_message_arrives",
    "emotional_damage_reconstruction",
    "council_of_judgment",
    "culprit_line_zoom",
    "dramatic_misinterpretation",
    "final_verdict",
    "end_card_roast",
]


SCRIPT_SCHEMA_HINT = """
Return ONLY valid JSON with this exact shape:

{
  "movie_title": string,
  "logline": string,
  "genre": string,
  "tone": string,
  "estimated_runtime_seconds": number,
  "narration": {
    "voice_direction": string,
    "full_script": string,
    "music": string
  },
  "scenes": [
    {
      "scene_id": string,
      "scene_template": string,
      "duration_seconds": number,
      "narration": string,
      "image_prompt": string,
      "negative_prompt": string,
      "on_screen_text": string
    }
  ],
  "title_card": string,
  "final_card": string,
  "visual_direction": string,
  "share_caption": string
}
"""


def build_system_prompt(
    runtime_seconds: int = 60,
    scene_count: int = 8,
) -> str:

    return f"""
You are YeOldeCut, a cinematic scriptwriter and emotionally unserious medieval narrator.

Your job is to transform rejection letters, breakup messages, investor rejections,
job rejections, ghosting explanations, or disappointing texts into a short cinematic roast film.

The user may provide:
- pasted text,
- an uploaded image or screenshot,
- or both.

If an image is provided, read the visible message from the image.
Do not output a full OCR transcript.
Use the content of the image as the source message.


The output will be used by a pipeline that:
1. generates images from your scene prompts,
2. generates narration with TTS,
3. stitches images, subtitles, and narration into a short MP4.

You must return strict JSON only.

Creative direction:
- Approximate runtime: {runtime_seconds} seconds
- Number of scenes: {scene_count}
- Style: Old English King James Version, faux-medieval, Shakespearean, sarcastic, cinematic, dramatic, funny
- Roast the message and the situation, the user's vulnerability and shortcomings.
- Be witty, theatrical, and emotionally validating.
- The narration should sound good when spoken aloud.
- Each scene needs an image_prompt suitable for a text-to-image model.
- Image prompts should be cinematic, detailed, and visually varied.
- Do not request text rendering inside generated images except simple title-card vibes.
- Keep on_screen_text short and let the video editor render it.
- Music should be instrumental and specific.

Voice direction must be generic, for example:
"Deep, warm, cinematic narrator; slow, dramatic, dry humor."

Available scene templates:
{json.dumps(SCENE_TEMPLATES, indent=2)}

{SCRIPT_SCHEMA_HINT}
""".strip()


def image_block(image: Union[str, Path, Any]) -> Dict[str, Any]:
    """
    Supports:
    - URL string
    - local filepath string
    - pathlib.Path
    - PIL image object, depending on processor support
    """

    if isinstance(image, Path):
        return {"type": "image", "path": str(image)}

    if isinstance(image, str):
        if image.startswith("http://") or image.startswith("https://"):
            return {"type": "image", "url": image}

        return {"type": "image", "path": image}

    return {"type": "image", "image": image}


def build_script_messages(
    rejection_text: Optional[str] = None,
    image: Optional[Union[str, Path, Any]] = None,
    runtime_seconds: int = 60,
    scene_count: int = 8,
) -> List[Dict[str, Any]]:
    """
    Builds multimodal chat messages for:
    - text-only input,
    - image-only input,
    - or image + text input.
    """

    system_prompt = build_system_prompt(
        runtime_seconds=runtime_seconds,
        scene_count=scene_count,
    )

    clean_text = (rejection_text or "").strip()[:6000]

    user_instruction = """
Transform the provided rejection, breakup, ghosting, investor rejection, or disappointment message
into the cinematic short-film JSON.

If an image is attached, read the visible text in the image and use it as the source.
If pasted text is also provided, combine both sources intelligently.
Return JSON only.
""".strip()

    content: List[Dict[str, Any]] = []

    if image is not None:
        content.append(image_block(image))

    if clean_text:
        content.append(
            {
                "type": "text",
                "text": f'{user_instruction}\n\nPasted text:\n"""\n{clean_text}\n"""',
            }
        )
    else:
        content.append(
            {
                "type": "text",
                "text": user_instruction,
            }
        )

    return [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": content,
        },
    ]
