from pathlib import Path
from threading import Lock
import uuid

from runtime_cache import configure_hf_cache

configure_hf_cache()

import torch
from diffusers import Flux2KleinPipeline

from director.device import pick_device


MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
_PIPE_LOCK = Lock()
_PIPE = None


def _image_pipeline():
    global _PIPE

    if _PIPE is not None:
        return _PIPE

    with _PIPE_LOCK:
        if _PIPE is not None:
            return _PIPE

        device, float_type = pick_device()
        pipe = Flux2KleinPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=float_type,
        )
        if device == "cuda":
            pipe.enable_model_cpu_offload()
        else:
            pipe.to(device)
        _PIPE = pipe
        return pipe


def generate_images(prompts, out_dir="outputs", seed=0):
    device, _ = pick_device()
    pipe = _image_pipeline()

    if isinstance(prompts, str):
        prompts = [prompts]

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    file_names = []

    for i, prompt in enumerate(prompts):
        generator = torch.Generator(device=device).manual_seed(seed + i)

        with torch.inference_mode():
            image = pipe(
                prompt=prompt,
                height=768,
                width=768,
                guidance_scale=1.0,
                num_inference_steps=4,
                generator=generator,
            ).images[0]

        file_name = Path(out_dir) / f"{uuid.uuid4()}.png"
        image.save(file_name)
        file_names.append(str(file_name))

        del image

    return file_names
