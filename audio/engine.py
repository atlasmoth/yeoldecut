from pathlib import Path
import uuid
from voxcpm import VoxCPM
import soundfile as sf


def generate_voice(text, out_dir="outputs", voice_direction=None):
    model = VoxCPM.from_pretrained(
        "openbmb/VoxCPM2",
        load_denoiser=False,
    )
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
