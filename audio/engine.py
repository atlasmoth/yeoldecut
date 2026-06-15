from voxcpm import VoxCPM
import soundfile as sf
import uuid


def generate_voice(text):
    model = VoxCPM.from_pretrained(
        "openbmb/VoxCPM2",
        load_denoiser=False,
    )
    wav = model.generate(
        text=f"(Middle-aged black man, deep baritone, warm, slow cinematic narrator) {text}",
        cfg_value=2.0,
        inference_timesteps=10,
    )

    file_name = f"{str(uuid.uuid4())}.wav"
    sf.write(file_name, wav, model.tts_model.sample_rate)
    print(f"saved: {file_name}")
