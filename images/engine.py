import torch
from diffusers import Flux2KleinPipeline
from director.device import pick_device
from pathlib import Path
import uuid


def generate_images(prompts, out_dir="outputs", seed=0):
    device, float_type = pick_device()

    pipe = Flux2KleinPipeline.from_pretrained(
        "black-forest-labs/FLUX.2-klein-4B",
        torch_dtype=float_type,
    )

    pipe.enable_model_cpu_offload()

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
