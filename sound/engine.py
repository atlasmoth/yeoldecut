import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration
from director.device import pick_device
import scipy.io.wavfile
import uuid


def generate_sound(text: str) -> str:
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

    file_name = f"{uuid.uuid4()}.wav"

    scipy.io.wavfile.write(
        file_name,
        rate=sampling_rate,
        data=audio,
    )

    return file_name
