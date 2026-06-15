from typing import Any, Dict, Optional, Union
from pathlib import Path
import json
import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM

from director.device import pick_device
from director.script_utils import (
    build_script_messages,
)


def substring_from_first_to_last_brace(s: str) -> str | None:
    start = s.find("{")
    end = s.rfind("}")

    if start == -1 or end == -1 or start > end:
        return None

    return s[start : end + 1]


def run_model(
    rejection_text: Optional[str] = None,
    image: Optional[Union[str, Path, Any]] = None,
    runtime_seconds: int = 60,
    scene_count: int = 8,
) -> Optional[Union[Dict[str, Any], str]]:
    # MODEL_ID = "Qwen/Qwen3.5-4B"

    MODEL_ID = "google/gemma-4-E2B-it"

    device, float_type = pick_device()

    processor = AutoProcessor.from_pretrained(MODEL_ID)

    model = AutoModelForMultimodalLM.from_pretrained(
        MODEL_ID,
        dtype=float_type,
    ).to(device)

    model.eval()

    if not rejection_text and image is None:
        rejection_text = (
            "The user received a vague rejection message with no useful explanation."
        )

    script_messages = build_script_messages(
        rejection_text=rejection_text,
        image=image,
        runtime_seconds=runtime_seconds,
        scene_count=scene_count,
    )

    try:

        kwargs = dict(
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )

        inputs = processor.apply_chat_template(
            script_messages,
            enable_thinking=False,
            **kwargs,
        ).to(model.device)

        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=2600,
                do_sample=True,
                temperature=1.0,
                top_p=0.95,
                top_k=64,
            )
        input_len = inputs["input_ids"].shape[-1]
        response = processor.decode(outputs[0][input_len:], skip_special_tokens=False)
        content = substring_from_first_to_last_brace(
            processor.parse_response(response).get("content")
        )
        return json.loads(content)

    except Exception as e:
        print(f"LLM script generation failed: {e}")
        return None
