import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration
from director.device import pick_device
from pathlib import Path
import scipy.io.wavfile
import uuid


def generate_sound(text: str, out_dir="outputs") -> str:
    device, float_type = pick_device()

    MODEL_ID = "facebook/musicgen-medium"

    processor = AutoProcessor.from_pretrained(MODEL_ID)

    model = MusicgenForConditionalGeneration.from_pretrained(
        MODEL_ID,
        torch_dtype=float_type,
    ).to(device)

    model.eval()

    inputs = processor(
        text=[text],
        padding=True,
        return_tensors="pt",
    ).to(device)

    with torch.inference_mode():
        audio_values = model.generate(
            **inputs,
            max_new_tokens=2600,
            do_sample=True,
        )

    sampling_rate = model.config.audio_encoder.sampling_rate

    audio = audio_values[0, 0].detach().cpu().float().numpy()

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    file_name = Path(out_dir) / f"{uuid.uuid4()}.wav"

    scipy.io.wavfile.write(
        str(file_name),
        rate=sampling_rate,
        data=audio,
    )

    return str(file_name)
