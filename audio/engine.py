from pathlib import Path
from threading import Lock
import uuid

from runtime_cache import configure_hf_cache

configure_hf_cache()

from voxcpm import VoxCPM
import soundfile as sf


MODEL_ID = "openbmb/VoxCPM2"
_VOICE_LOCK = Lock()
_VOICE_MODEL = None


def _voice_model():
    global _VOICE_MODEL

    if _VOICE_MODEL is not None:
        return _VOICE_MODEL

    with _VOICE_LOCK:
        if _VOICE_MODEL is not None:
            return _VOICE_MODEL

        model = VoxCPM.from_pretrained(
            MODEL_ID,
            load_denoiser=False,
        )
        _VOICE_MODEL = model
        return model


def generate_voice(text, out_dir="outputs", voice_direction=None):
    model = _voice_model()
    style = voice_direction or "Deep, warm, cinematic narrator; slow, dramatic, dry humor."
    wav = model.generate(
        text=f"(Middle-aged black male, deep base and baritone, slow, {style}) {text}",
        cfg_value=2.0,
        inference_timesteps=10,
    )

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    file_name = Path(out_dir) / f"{uuid.uuid4()}.wav"
    sf.write(str(file_name), wav, model.tts_model.sample_rate)
    print(f"saved: {file_name}")
    return str(file_name)
