from pathlib import Path
from threading import Lock
import uuid

from runtime_cache import configure_hf_cache

configure_hf_cache()

import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

from director.device import pick_device
import scipy.io.wavfile


MODEL_ID = "facebook/musicgen-medium"
_MUSIC_LOCK = Lock()
_MUSIC_PROCESSOR = None
_MUSIC_MODEL = None


def _music_components():
    global _MUSIC_PROCESSOR, _MUSIC_MODEL

    if _MUSIC_PROCESSOR is not None and _MUSIC_MODEL is not None:
        return _MUSIC_PROCESSOR, _MUSIC_MODEL

    with _MUSIC_LOCK:
        if _MUSIC_PROCESSOR is not None and _MUSIC_MODEL is not None:
            return _MUSIC_PROCESSOR, _MUSIC_MODEL

        device, float_type = pick_device()
        processor = AutoProcessor.from_pretrained(MODEL_ID)
        model = MusicgenForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=float_type,
        ).to(device)
        model.eval()

        _MUSIC_PROCESSOR = processor
        _MUSIC_MODEL = model
        return processor, model


def generate_sound(text: str, out_dir="outputs") -> str:
    device, _ = pick_device()
    processor, model = _music_components()

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
