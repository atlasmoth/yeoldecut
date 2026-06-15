from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import json
import uuid

from runtime_cache import configure_hf_cache

configure_hf_cache()

import spaces

from audio.engine import generate_voice
from director.engine import run_model
from images.engine import generate_images
from sound.engine import generate_sound
from video.engine import compose_movie


DEFAULT_MUSIC_PROMPT = "small medieval chamber orchestra, warm lute, low cinematic drums, dry comedy timing"


def _scene_image_prompts(script: dict[str, Any]) -> list[str]:
    prompts: list[str] = []
    for scene in script.get("scenes") or []:
        prompt = scene.get("image_prompt") or "cinematic faux-medieval parchment courtroom, dramatic comedy"
        negative_prompt = scene.get("negative_prompt")
        if negative_prompt:
            prompt = f"{prompt} Negative prompt: {negative_prompt}"
        prompts.append(prompt)
    return prompts


def _write_script(script: dict[str, Any], out_dir: Path) -> str:
    script_path = out_dir / "script.json"
    script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(script_path)


@spaces.GPU(duration=600)
def generate_roast_movie(
    rejection_text: str | None = None,
    image: str | Path | Any | None = None,
    runtime_seconds: int = 60,
    scene_count: int = 6,
    out_root: str | Path = "outputs",
    progress_callback: Callable[[float, str], None] | None = None,
) -> dict[str, Any]:
    def tick(value: float, message: str) -> None:
        if progress_callback:
            progress_callback(value, message)

    if not (rejection_text or "").strip() and image is None:
        raise ValueError("Paste a message, upload a screenshot, or do both.")

    run_id = uuid.uuid4().hex[:10]
    out_dir = Path(out_root) / run_id
    audio_dir = out_dir / "audio"
    image_dir = out_dir / "images"
    video_dir = out_dir / "video"
    out_dir.mkdir(parents=True, exist_ok=True)

    tick(0.08, "Convening the tiny court")
    script = run_model(
        rejection_text=(rejection_text or "").strip() or None,
        image=image,
        runtime_seconds=runtime_seconds,
        scene_count=scene_count,
    )

    if not isinstance(script, dict):
        raise RuntimeError("The director model did not return a usable script.")

    tick(0.24, "Writing the illuminated script")
    narration = script.get("narration") or {}
    transcript = narration.get("full_script") or "The court has reviewed the evidence and finds the vibes dramatic."
    music_prompt = narration.get("music") or DEFAULT_MUSIC_PROMPT
    voice_direction = narration.get("voice_direction")

    script_path = _write_script(script, out_dir)
    tick(0.34, "Scoring the public humiliation")
    music_path = generate_sound(music_prompt, out_dir=audio_dir)
    tick(0.50, "Summoning the narrator")
    voice_path = generate_voice(transcript, out_dir=audio_dir, voice_direction=voice_direction)
    tick(0.66, "Painting the evidence")
    image_paths = generate_images(_scene_image_prompts(script), out_dir=image_dir)
    tick(0.84, "Cutting the final motion picture")
    video_path = compose_movie(
        script=script,
        image_paths=image_paths,
        narration_path=voice_path,
        music_path=music_path,
        out_dir=video_dir,
    )
    tick(0.98, "Sealing the verdict")

    return {
        "run_id": run_id,
        "out_dir": str(out_dir),
        "script": script,
        "script_path": script_path,
        "music_path": music_path,
        "voice_path": voice_path,
        "image_paths": image_paths,
        "video_path": video_path,
        "share_caption": script.get("share_caption") or "",
    }
