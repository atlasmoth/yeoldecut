from __future__ import annotations

import os
from pathlib import Path


def _is_writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def configure_hf_cache() -> Path:
    """Prefer persistent Spaces storage for downloaded model weights."""
    configured = os.environ.get("HF_HOME")
    if configured:
        cache_root = Path(configured).expanduser()
    else:
        candidates: list[Path] = []
        if custom_cache := os.environ.get("YEOLDECUT_HF_CACHE"):
            candidates.append(Path(custom_cache).expanduser())
        if Path("/data").exists():
            candidates.append(Path("/data/.huggingface"))
        candidates.append(Path(".cache/huggingface"))

        cache_root = next((path for path in candidates if _is_writable_directory(path)), candidates[-1])
        os.environ["HF_HOME"] = str(cache_root)

    hub_cache = cache_root / "hub"
    hub_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HUB_CACHE", str(hub_cache))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hub_cache))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(hub_cache))
    os.environ.setdefault("DIFFUSERS_CACHE", str(hub_cache))
    return cache_root


HF_CACHE_HOME = configure_hf_cache()


import torch


def pick_device() -> tuple[str, torch.dtype]:
    if torch.cuda.is_available():
        return "cuda", torch.float16

    if torch.backends.mps.is_available():
        return "mps", torch.float16

    return "cpu", torch.float32
