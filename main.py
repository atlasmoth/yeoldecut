from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import quote
import html
import shutil
import uuid

import gradio as gr
from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from pipeline import generate_roast_movie


APP_TITLE = "YeOldeCut"
APP_TAGLINE = "A tiny theatre for texts that deserved better."
ROOT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT_DIR / "outputs"
UPLOAD_DIR = OUTPUTS_DIR / "_uploads"

EXAMPLES = {
    "job": "Thanks for applying. We enjoyed learning about your background, but we have decided to move forward with candidates whose experience more closely matches the role.",
    "dating": "I think you are great, but I am not really looking for anything serious right now. I hope you understand.",
    "investor": "We loved the energy, but the fund is going to pass for now. The market feels a little early and we want to see more traction before revisiting.",
}

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = Lock()
EXECUTOR = ThreadPoolExecutor(max_workers=1)


def _artifact_url(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(ROOT_DIR)
    except ValueError:
        relative = resolved.relative_to(OUTPUTS_DIR)
        relative = Path("outputs") / relative
    return f"/artifact/{quote(relative.as_posix())}"


def _set_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        JOBS.setdefault(job_id, {}).update(updates)


def _get_job(job_id: str) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Performance not found.")
        return dict(job)


def _save_upload(job_id: str, upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename).suffix or ".png"
    path = UPLOAD_DIR / f"{job_id}{suffix}"
    with path.open("wb") as file:
        shutil.copyfileobj(upload.file, file)
    return str(path)


def _run_job(
    job_id: str,
    message: str,
    screenshot_path: str | None,
    runtime_seconds: int,
    scene_count: int,
) -> None:
    def progress(value: float, line: str) -> None:
        _set_job(job_id, status="running", progress=value, line=line)

    try:
        progress(0.04, "The house lights fall.")
        result = generate_roast_movie(
            rejection_text=message,
            image=screenshot_path,
            runtime_seconds=runtime_seconds,
            scene_count=scene_count,
            progress_callback=progress,
        )
        script = result.get("script") or {}
        downloads = [
            {"label": "Final film", "url": _artifact_url(result["video_path"])},
            {"label": "Share caption", "url": _artifact_url(result["script_path"])},
            {"label": "Narration", "url": _artifact_url(result["voice_path"])},
            {"label": "Score", "url": _artifact_url(result["music_path"])},
        ]
        for index, image_path in enumerate(result.get("image_paths") or [], start=1):
            downloads.append({"label": f"Still {index}", "url": _artifact_url(image_path)})

        _set_job(
            job_id,
            status="done",
            progress=1.0,
            line="The curtain opens.",
            result={
                "title": script.get("movie_title") or "The Court Has Spoken",
                "logline": script.get("logline") or "A private text became public theatre.",
                "caption": result.get("share_caption") or "",
                "video_url": _artifact_url(result["video_path"]),
                "downloads": downloads,
            },
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="error",
            progress=1.0,
            line="The performance stumbled before the final bow.",
            error=str(exc),
        )


def create_server() -> gr.Server:
    server = gr.Server(
        title=APP_TITLE,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @server.get("/", response_class=HTMLResponse)
    def theatre() -> str:
        return THEATRE_HTML

    @server.post("/api/perform")
    async def perform(
        message: str = Form(""),
        runtime_seconds: int = Form(60),
        scene_count: int = Form(6),
        screenshot: UploadFile | None = File(None),
    ) -> JSONResponse:
        clean_message = (message or "").strip()
        if not clean_message and not (screenshot and screenshot.filename):
            raise HTTPException(
                status_code=400,
                detail="Bring a message or screenshot to the stage first.",
            )

        job_id = uuid.uuid4().hex[:12]
        screenshot_path = _save_upload(job_id, screenshot)
        _set_job(
            job_id,
            status="queued",
            progress=0.01,
            line="The theatre inhales.",
        )
        EXECUTOR.submit(
            _run_job,
            job_id,
            clean_message,
            screenshot_path,
            int(runtime_seconds),
            int(scene_count),
        )
        return JSONResponse({"job_id": job_id})

    @server.get("/api/perform/{job_id}")
    def perform_status(job_id: str) -> JSONResponse:
        return JSONResponse(_get_job(job_id))

    @server.get("/artifact/{path:path}")
    def artifact(path: str) -> FileResponse:
        target = (ROOT_DIR / path).resolve()
        outputs_root = OUTPUTS_DIR.resolve()
        if not str(target).startswith(str(outputs_root)) or not target.exists():
            raise HTTPException(status_code=404, detail="Artifact not found.")
        return FileResponse(target)

    return server


def launch_app() -> None:
    server.launch(
        server_name="0.0.0.0",
        show_error=True,
        _frontend=False,
    )


def _example_attr(key: str) -> str:
    return html.escape(EXAMPLES[key], quote=True)


THEATRE_HTML = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#080504">
  <title>{APP_TITLE}</title>
  <style>
    :root {{
      --blood: #7f1d18;
      --blood-lit: #be4931;
      --gold: #e0ad57;
      --gold-soft: rgba(224, 173, 87, 0.2);
      --velvet: #180806;
      --velvet-deep: #080504;
      --smoke: rgba(255, 244, 217, 0.72);
      --paper: #f0d8a5;
      --ink: #21130d;
      --line: rgba(240, 216, 165, 0.2);
    }}

    * {{
      box-sizing: border-box;
    }}

    html {{
      min-height: 100%;
      background: var(--velvet-deep);
      color: var(--paper);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    body {{
      min-height: 100vh;
      margin: 0;
      overflow-x: hidden;
      background:
        radial-gradient(circle at 50% -18%, rgba(255, 214, 126, 0.18), transparent 34rem),
        radial-gradient(circle at 12% 42%, rgba(190, 73, 49, 0.18), transparent 24rem),
        linear-gradient(180deg, #120604 0%, #080504 48%, #050303 100%);
    }}

    button,
    textarea,
    input {{
      font: inherit;
    }}

    .theatre {{
      position: relative;
      min-height: 100vh;
      isolation: isolate;
    }}

    .theatre::before,
    .theatre::after {{
      content: "";
      position: fixed;
      top: -8vh;
      bottom: -10vh;
      width: min(21vw, 280px);
      z-index: -1;
      background:
        repeating-linear-gradient(90deg, rgba(255,255,255,0.035) 0 2px, transparent 2px 34px),
        linear-gradient(90deg, #260805, #7d211a 45%, #260805);
      filter: drop-shadow(0 0 32px rgba(0,0,0,0.55));
      opacity: 0.92;
    }}

    .theatre::before {{
      left: 0;
      transform: skewX(-4deg);
      border-right: 1px solid rgba(224,173,87,0.25);
    }}

    .theatre::after {{
      right: 0;
      transform: skewX(4deg);
      border-left: 1px solid rgba(224,173,87,0.25);
    }}

    .light-cone {{
      position: fixed;
      left: 50%;
      top: -14vh;
      width: min(88vw, 1080px);
      height: 78vh;
      transform: translateX(-50%);
      z-index: -1;
      background: radial-gradient(ellipse at top, rgba(255, 236, 179, 0.2), rgba(224, 173, 87, 0.07) 34%, transparent 69%);
      clip-path: polygon(34% 0, 66% 0, 100% 100%, 0 100%);
      animation: breathe 6s ease-in-out infinite;
    }}

    @keyframes breathe {{
      0%, 100% {{ opacity: 0.72; }}
      50% {{ opacity: 1; }}
    }}

    .house {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 18px 0 44px;
    }}

    .mast {{
      min-height: auto;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 14px;
    }}

    .marquee {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: center;
      padding: 6px 6px 0;
      color: rgba(240, 216, 165, 0.78);
      text-transform: uppercase;
      font-size: 12px;
      font-weight: 850;
    }}

    .marquee span {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }}

    .marquee span::before,
    .marquee span::after {{
      content: "";
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: var(--gold);
      box-shadow: 0 0 18px var(--gold);
    }}

    .stage {{
      position: relative;
      overflow: hidden;
      display: grid;
      place-items: center;
      min-height: clamp(310px, 43vh, 500px);
      border-radius: 0;
      border: 0;
      background:
        radial-gradient(ellipse at 50% 72%, rgba(224, 173, 87, 0.22), transparent 26rem),
        linear-gradient(180deg, rgba(255,255,255,0.04), transparent 24%),
        transparent;
      box-shadow:
        inset 0 -120px 120px rgba(0,0,0,0.2);
    }}

    .stage::before {{
      content: "";
      position: absolute;
      inset: -8% 8% 0;
      background:
        radial-gradient(ellipse at 50% 42%, rgba(255, 236, 179, 0.12), transparent 38%),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.02) 0 1px, transparent 1px 58px);
      pointer-events: none;
      mask-image: radial-gradient(ellipse, black 0 58%, transparent 76%);
    }}

    .stage::after {{
      content: "";
      position: absolute;
      left: 8%;
      right: 8%;
      bottom: -7%;
      height: 22%;
      border-radius: 50%;
      background: radial-gradient(ellipse, rgba(224, 173, 87, 0.36), rgba(54, 22, 10, 0.2) 42%, transparent 72%);
      filter: blur(5px);
    }}

    .title-scene {{
      position: relative;
      z-index: 2;
      width: min(920px, calc(100% - 42px));
      text-align: center;
      padding: clamp(32px, 6vh, 54px) 0 clamp(14px, 2vh, 22px);
    }}

    .sigil {{
      margin: 0 auto 18px;
      width: min(360px, 72vw);
      border-top: 1px solid rgba(224,173,87,0.68);
      border-bottom: 1px solid rgba(224,173,87,0.35);
      padding: 9px 0;
      color: var(--gold);
      text-transform: uppercase;
      font-size: 12px;
      font-weight: 900;
    }}

    h1 {{
      margin: 0;
      color: #fff3cf;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(46px, 9.2vw, 116px);
      line-height: 0.9;
      font-weight: 900;
      letter-spacing: 0;
      text-shadow: 0 8px 0 rgba(67, 22, 14, 0.58), 0 0 50px rgba(224,173,87,0.18);
    }}

    .tagline {{
      max-width: 660px;
      margin: 18px auto 0;
      color: var(--smoke);
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(20px, 2.5vw, 34px);
      line-height: 1.08;
    }}

    .whisper {{
      max-width: 620px;
      margin: 14px auto 0;
      color: rgba(240, 216, 165, 0.66);
      font-size: 15px;
      line-height: 1.55;
    }}

    .success-scene {{
      position: relative;
      z-index: 3;
      display: none;
      width: min(720px, calc(100% - 42px));
      place-items: center;
      text-align: center;
      padding: clamp(36px, 6vh, 64px) 0 clamp(18px, 3vh, 30px);
    }}

    .success-scene::before,
    .success-scene::after {{
      content: "";
      position: absolute;
      left: 50%;
      width: min(520px, 72vw);
      height: 1px;
      transform: translateX(-50%);
      background: linear-gradient(90deg, transparent, rgba(224,173,87,0.78), transparent);
      box-shadow: 0 0 26px rgba(224,173,87,0.34);
      pointer-events: none;
    }}

    .success-scene::before {{
      top: 14px;
    }}

    .success-scene::after {{
      bottom: 4px;
    }}

    .success-mark {{
      width: 92px;
      height: 92px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      color: #2a0d08;
      background:
        radial-gradient(circle at 50% 18%, rgba(255,255,255,0.46), transparent 42%),
        linear-gradient(135deg, #ffe6a9, var(--gold));
      box-shadow: 0 18px 46px rgba(224,173,87,0.26), 0 0 0 12px rgba(224,173,87,0.08);
      font-family: Georgia, "Times New Roman", serif;
      font-size: 28px;
      font-weight: 900;
      letter-spacing: 0.04em;
      margin-bottom: 22px;
      animation: sealGlow 2.8s ease-in-out infinite;
    }}

    .success-scene h2 {{
      margin: 0;
      color: #fff3cf;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(34px, 5vw, 66px);
      line-height: 0.98;
      text-shadow: 0 8px 0 rgba(67, 22, 14, 0.5), 0 0 48px rgba(224,173,87,0.2);
      animation: verdictRise 700ms ease both;
    }}

    .success-scene p {{
      max-width: 580px;
      margin: 16px auto 0;
      color: rgba(255, 244, 217, 0.76);
      font-size: clamp(16px, 2vw, 20px);
      line-height: 1.5;
      animation: verdictRise 700ms ease 90ms both;
    }}

    .watch {{
      margin-top: 28px;
      min-height: 62px;
      border: 0;
      border-radius: 999px;
      padding: 15px 26px;
      color: #21130d;
      background:
        radial-gradient(circle at 50% 0, rgba(255,255,255,0.36), transparent 42%),
        linear-gradient(135deg, #ffe7ad, #d6983e 78%);
      box-shadow: 0 24px 62px rgba(224,173,87,0.28), inset 0 0 0 1px rgba(255,255,255,0.42);
      cursor: pointer;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 21px;
      font-weight: 900;
      animation: verdictRise 700ms ease 180ms both;
    }}

    .watch:disabled {{
      opacity: 0.58;
      cursor: wait;
    }}

    .watch:not(:disabled):hover {{
      transform: translateY(-2px);
      box-shadow: 0 28px 76px rgba(224,173,87,0.36), inset 0 0 0 1px rgba(255,255,255,0.5);
    }}

    @keyframes verdictRise {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes sealGlow {{
      0%, 100% {{ transform: scale(1); box-shadow: 0 18px 46px rgba(224,173,87,0.26), 0 0 0 12px rgba(224,173,87,0.08); }}
      50% {{ transform: scale(1.04); box-shadow: 0 24px 66px rgba(224,173,87,0.38), 0 0 0 16px rgba(224,173,87,0.1); }}
    }}

    .stage.has-result .title-scene {{
      display: none;
    }}

    .stage.has-result .success-scene {{
      display: grid;
    }}

    .stage.is-performing .title-scene {{
      transform: translateY(-6px);
      transition: transform 700ms ease;
    }}

    .stage.is-performing .sigil {{
      animation: pulseLine 1.4s ease-in-out infinite;
    }}

    @keyframes pulseLine {{
      0%, 100% {{ opacity: 0.55; }}
      50% {{ opacity: 1; }}
    }}

    .orchestra {{
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 12px;
      justify-items: center;
      padding: 0 6px;
      margin-top: -28px;
      z-index: 5;
    }}

    .composer {{
      width: min(980px, 100%);
      display: grid;
      gap: 8px;
      justify-items: start;
    }}

    .note {{
      position: relative;
      overflow: visible;
      width: 100%;
      border-radius: 999px;
      background:
        linear-gradient(135deg, rgba(251, 229, 184, 0.98), rgba(204, 145, 74, 0.95)),
        var(--paper);
      color: var(--ink);
      box-shadow: 0 20px 64px rgba(0,0,0,0.42), inset 0 0 0 1px rgba(255,255,255,0.44);
      transform: none;
    }}

    .note::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at 18% 20%, rgba(255,255,255,0.24), transparent 13rem);
      border-radius: inherit;
      pointer-events: none;
    }}

    .note-inner {{
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 12px;
      padding: 10px 12px 10px 22px;
    }}

    textarea {{
      width: 100%;
      min-height: 50px;
      max-height: 76px;
      resize: none;
      overflow: auto;
      border: 0;
      outline: 0;
      border-radius: 999px;
      padding: 15px 24px 13px 18px;
      background: transparent;
      color: var(--ink);
      font-size: 16px;
      line-height: 1.35;
      box-shadow: none;
    }}

    textarea::-webkit-scrollbar {{
      width: 0;
      height: 0;
    }}

    textarea::placeholder {{
      color: rgba(33, 19, 13, 0.54);
    }}

    .props {{
      width: auto;
      display: flex;
      align-items: center;
      gap: 0;
      justify-items: center;
    }}

    .upload {{
      position: relative;
      display: grid;
      place-items: center;
      width: 54px;
      height: 54px;
      min-height: 54px;
      border: 1px solid rgba(33, 19, 13, 0.24);
      border-radius: 999px;
      text-align: center;
      color: #fff2ce;
      cursor: pointer;
      background:
        radial-gradient(circle at 50% 15%, rgba(255,255,255,0.26), transparent 38%),
        linear-gradient(135deg, #ae3928, #64140f 76%);
      box-shadow: 0 10px 26px rgba(96, 18, 12, 0.28);
      font-size: 0;
      flex: 0 0 auto;
    }}

    .upload span::before {{
      content: "+";
      display: grid;
      place-items: center;
      width: 100%;
      height: 100%;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 34px;
      line-height: 1;
      font-weight: 900;
    }}

    .upload input {{
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }}

    .prompt-borrow {{
      display: grid;
      justify-items: center;
      gap: 10px;
      color: #ffe8b7;
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
      padding-top : 1.5rem;
      padding-bottom : 1.5rem;
    }}

    .prompt-borrow > span {{
      border: 1px solid rgba(224, 173, 87, 0.34);
      border-radius: 999px;
      padding: 7px 14px;
      background: rgba(20, 7, 5, 0.54);
      box-shadow: 0 10px 26px rgba(0,0,0,0.24), inset 0 0 0 1px rgba(255,255,255,0.05);
      text-shadow: 0 1px 12px rgba(224, 173, 87, 0.36);
      margin-bottom : 0.5rem;
    }}

    .chips {{
      justify-content: center;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .chip {{
      border: 1px solid rgba(255, 242, 206, 0.42);
      border-radius: 999px;
      padding: 9px 13px;
      background: rgba(240, 216, 165, 0.88);
      color: var(--ink);
      cursor: pointer;
      font-weight: 760;
      box-shadow: 0 12px 26px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.34);
    }}

    .call {{
      position: relative;
      overflow: hidden;
      display: grid;
      place-items: center;
      width: min(430px, 100%);
      min-height: 76px;
      border: 0;
      border-radius: 999px;
      padding: 18px 28px;
      color: #fff2ce;
      background:
        radial-gradient(circle at 50% 0, rgba(255,255,255,0.22), transparent 38%),
        linear-gradient(135deg, #b83927, #63140f 78%);
      box-shadow: 0 28px 72px rgba(96, 18, 12, 0.54), inset 0 0 0 1px rgba(255,255,255,0.22);
      font-family: Georgia, "Times New Roman", serif;
      font-size: 23px;
      font-weight: 900;
      cursor: pointer;
      text-align: center;
      transition: filter 180ms ease, opacity 180ms ease, transform 180ms ease;
    }}

    .call::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(110deg, transparent 0 34%, rgba(255,255,255,0.28) 46%, transparent 58%);
      opacity: 0;
      transform: translateX(-120%);
      pointer-events: none;
    }}

    .call-text {{
      position: relative;
      z-index: 1;
    }}

    .call.is-loading {{
      filter: none;
      opacity: 1;
      cursor: wait;
      box-shadow: 0 32px 88px rgba(184, 57, 39, 0.64), inset 0 0 0 1px rgba(255,255,255,0.26);
      animation: buttonPulse 1.9s ease-in-out infinite;
    }}

    .call.is-loading::before {{
      opacity: 1;
      animation: curtainSweep 2.4s ease-in-out infinite;
    }}

    .call.is-loading .call-text {{
      animation: loadingWords 2.4s ease-in-out infinite;
    }}

    .call:disabled:not(.is-loading) {{
      filter: grayscale(0.6);
      opacity: 0.64;
      cursor: not-allowed;
    }}

    @keyframes curtainSweep {{
      0% {{ transform: translateX(-120%); }}
      52%, 100% {{ transform: translateX(120%); }}
    }}

    @keyframes buttonPulse {{
      0%, 100% {{ transform: translateY(0); }}
      50% {{ transform: translateY(-2px); }}
    }}

    @keyframes loadingWords {{
      0%, 100% {{ opacity: 0.45; transform: translateY(2px); }}
      24%, 76% {{ opacity: 1; transform: translateY(0); }}
    }}

    .image-preview {{
      display: none;
      position: relative;
      width: 58px;
      aspect-ratio: 1;
      justify-self: start;
      overflow: hidden;
      border-radius: 14px;
      border: 1px solid rgba(224, 173, 87, 0.34);
      background: rgba(255, 244, 217, 0.08);
      box-shadow: 0 10px 26px rgba(0,0,0,0.26);
    }}

    .image-preview.show {{
      display: block;
    }}

    .image-preview img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}

    .clear-image {{
      position: absolute;
      right: 4px;
      top: 4px;
      width: 20px;
      height: 20px;
      border: 0;
      border-radius: 999px;
      color: #fff2ce;
      background: rgba(20, 7, 5, 0.72);
      cursor: pointer;
      font-size: 12px;
      line-height: 1;
    }}

    .afterword {{
      display: none;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: end;
      padding: 18px 8px 0;
    }}

    .afterword.show {{
      display: grid;
    }}

    .review {{
      color: rgba(240,216,165,0.86);
    }}

    .review h2 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(26px, 4vw, 48px);
      line-height: 1;
      color: #fff2ce;
    }}

    .review p {{
      max-width: 680px;
      margin: 10px 0 0;
      color: rgba(240,216,165,0.68);
      line-height: 1.5;
    }}

    .downloads {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }}

    .downloads a {{
      border: 1px solid rgba(224,173,87,0.36);
      border-radius: 999px;
      padding: 9px 12px;
      color: #ffe7ad;
      text-decoration: none;
      background: rgba(224,173,87,0.1);
      font-size: 13px;
      font-weight: 820;
    }}

    .caption {{
      margin-top: 14px;
      width: min(720px, 100%);
      border-left: 2px solid rgba(224,173,87,0.56);
      padding-left: 14px;
      color: rgba(255,242,206,0.84);
      font-size: 15px;
      line-height: 1.5;
    }}

    .error {{
      color: #ffd2c2;
    }}

    .film-modal {{
      position: fixed;
      inset: 0;
      z-index: 30;
      display: none;
      place-items: center;
      padding: clamp(18px, 4vw, 46px);
      background:
        radial-gradient(circle at 50% 10%, rgba(224,173,87,0.16), transparent 28rem),
        rgba(5, 3, 3, 0.9);
      backdrop-filter: blur(16px);
    }}

    .film-modal.open {{
      display: grid;
    }}

    .film-shell {{
      width: min(92vw, 520px);
      max-height: min(92vh, 920px);
      display: grid;
      place-items: center;
    }}

    .film-frame {{
      width: min(92vw, 430px);
      aspect-ratio: 9 / 16;
      overflow: hidden;
      border-radius: 30px;
      border: 1px solid rgba(224, 173, 87, 0.5);
      background: #050303;
      box-shadow: 0 0 0 12px rgba(20, 7, 5, 0.62), 0 34px 110px rgba(0,0,0,0.86);
    }}

    .film-frame video {{
      width: 100%;
      height: 100%;
      display: block;
      object-fit: contain;
      background: #050303;
    }}

    .modal-close {{
      position: fixed;
      right: clamp(16px, 4vw, 34px);
      top: clamp(16px, 4vw, 34px);
      width: 46px;
      height: 46px;
      border: 1px solid rgba(255, 242, 206, 0.22);
      border-radius: 999px;
      color: #fff2ce;
      background: rgba(20, 7, 5, 0.72);
      cursor: pointer;
      font-size: 22px;
      font-weight: 800;
      line-height: 1;
      box-shadow: 0 14px 36px rgba(0,0,0,0.36);
    }}

    body.modal-open {{
      overflow: hidden;
    }}

    @media (max-width: 880px) {{
      .house {{
        width: min(100% - 18px, 620px);
        padding-top: 10px;
      }}

      .stage {{
        min-height: 330px;
        border-radius: 0;
      }}

      .title-scene {{
        padding-top: 38px;
      }}

      h1 {{
        font-size: clamp(48px, 16vw, 92px);
      }}

      .orchestra,
      .afterword {{
        grid-template-columns: 1fr;
      }}

      .call {{
        width: 100%;
        min-height: 72px;
      }}

      .note-inner {{
        padding-left: 18px;
      }}

      .theatre::before,
      .theatre::after {{
        width: 74px;
        opacity: 0.64;
      }}

      .marquee {{
        font-size: 10px;
      }}

      .downloads {{
        justify-content: flex-start;
      }}

      .film-frame {{
        width: min(82vw, 390px);
      }}
    }}
  </style>
</head>
<body>
  <main class="theatre">
    <div class="light-cone"></div>
    <div class="house">
      <section class="mast">
        <div class="marquee">
          <span>Now performing</span>
          <span>Admission: one terrible text</span>
        </div>

        <section id="stage" class="stage" aria-live="polite">
          <div class="title-scene">
            <div class="sigil">The Royal Theatre of Rejections</div>
            <h1>{APP_TITLE}</h1>
            <p class="tagline">{APP_TAGLINE}</p>
            <p class="whisper">Bring the message. The curtains will do the rest.</p>
          </div>
          <div class="success-scene" id="successScene">
            <div class="success-mark" aria-hidden="true">FIN</div>
            <h2 id="successTitle">The verdict has arrived.</h2>
            <p id="successCopy">The reel is sealed, the balcony is silent, and the court is prepared to be ridiculous.</p>
            <button id="watchFilm" class="watch" type="button" disabled>Enter the screening room</button>
          </div>
        </section>

        <form id="playbill" class="orchestra">
          <div class="composer">
            <div id="imagePreview" class="image-preview" aria-live="polite">
              <img id="previewImage" alt="Selected screenshot preview">
              <button id="clearImage" class="clear-image" type="button" aria-label="Remove selected image">x</button>
            </div>
            <div class="note">
              <div class="note-inner">
                <textarea id="message" name="message" placeholder="Paste the rejection, breakup, ghosting note, or polite corporate dagger here..."></textarea>
                <div class="props">
                  <label class="upload">
                    <input id="screenshot" name="screenshot" type="file" accept="image/*">
                    <span id="uploadLabel">Or slip in a screenshot</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
          <div class="prompt-borrow">
            <span>Borrow a dramatic prompt</span>
            <div class="chips">
              <button class="chip" type="button" data-example="{_example_attr('job')}">Job letter</button>
              <button class="chip" type="button" data-example="{_example_attr('dating')}">Soft heartbreak</button>
              <button class="chip" type="button" data-example="{_example_attr('investor')}">Investor pass</button>
            </div>
          </div>
          <button id="summon" class="call" type="submit"><span id="summonText" class="call-text">Raise the curtain</span></button>
        </form>

        <section id="afterword" class="afterword">
          <div class="review">
            <h2 id="title"></h2>
            <p id="logline"></p>
            <div id="caption" class="caption"></div>
          </div>
          <nav id="downloads" class="downloads" aria-label="Downloads"></nav>
        </section>
      </section>
    </div>
  </main>

  <div id="filmModal" class="film-modal" aria-hidden="true" role="dialog" aria-modal="true" aria-label="Generated performance">
    <button id="closeFilm" class="modal-close" type="button" aria-label="Close video">x</button>
    <div class="film-shell">
      <div class="film-frame">
        <video id="film" controls playsinline preload="metadata"></video>
      </div>
    </div>
  </div>

  <script>
    const stage = document.querySelector("#stage");
    const form = document.querySelector("#playbill");
    const message = document.querySelector("#message");
    const screenshot = document.querySelector("#screenshot");
    const uploadLabel = document.querySelector("#uploadLabel");
    const imagePreview = document.querySelector("#imagePreview");
    const previewImage = document.querySelector("#previewImage");
    const clearImage = document.querySelector("#clearImage");
    const summon = document.querySelector("#summon");
    const summonText = document.querySelector("#summonText");
    const successTitle = document.querySelector("#successTitle");
    const successCopy = document.querySelector("#successCopy");
    const watchFilm = document.querySelector("#watchFilm");
    const filmModal = document.querySelector("#filmModal");
    const closeFilm = document.querySelector("#closeFilm");
    const film = document.querySelector("#film");
    const afterword = document.querySelector("#afterword");
    const title = document.querySelector("#title");
    const logline = document.querySelector("#logline");
    const caption = document.querySelector("#caption");
    const downloads = document.querySelector("#downloads");

    const stageLines = [
      "The house lights fall.",
      "A quill scratches in the balcony.",
      "The chorus gasps quietly.",
      "Someone important adjusts a ridiculous hat.",
      "The spotlight searches for the wound.",
      "The curtain is thinking about it."
    ];
    const DEFAULT_RUNTIME_SECONDS = "60";
    const DEFAULT_SCENE_COUNT = "6";
    let lineTimer = null;
    let isPerforming = false;
    let previewUrl = null;
    let idleSummonText = "Raise the curtain";
    let currentVideoUrl = "";

    function hasEvidence() {{
      return Boolean(message.value.trim() || screenshot.files?.length);
    }}

    function setSummonText(text) {{
      summonText.textContent = text || idleSummonText;
    }}

    function updateSummonState() {{
      summon.disabled = isPerforming || !hasEvidence();
    }}

    function clearPreviewUrl() {{
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }}

    function updateImagePreview() {{
      clearPreviewUrl();
      const file = screenshot.files?.[0];
      uploadLabel.textContent = file?.name || "Or slip in a screenshot";

      if (!file) {{
        previewImage.removeAttribute("src");
        imagePreview.classList.remove("show");
        updateSummonState();
        return;
      }}

      previewUrl = URL.createObjectURL(file);
      previewImage.src = previewUrl;
      imagePreview.classList.add("show");
      updateSummonState();
    }}

    function setLoadingLine(text) {{
      if (isPerforming && text) setSummonText(text);
    }}

    function beginTheatreLines() {{
      let index = 0;
      clearInterval(lineTimer);
      setLoadingLine(stageLines[index]);
      index += 1;
      lineTimer = setInterval(() => {{
        if (!stage.classList.contains("is-performing")) return;
        setLoadingLine(stageLines[index % stageLines.length]);
        index += 1;
      }}, 2800);
    }}

    function stopTheatreLines() {{
      clearInterval(lineTimer);
      lineTimer = null;
      summon.classList.remove("is-loading");
    }}

    function openFilmModal() {{
      if (!currentVideoUrl) return;
      filmModal.classList.add("open");
      filmModal.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");
      film.focus();
    }}

    function closeFilmModal(returnFocus = true) {{
      film.pause();
      filmModal.classList.remove("open");
      filmModal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("modal-open");
      if (returnFocus) watchFilm.focus();
    }}

    document.querySelectorAll("[data-example]").forEach((button) => {{
      button.addEventListener("click", () => {{
        message.value = button.dataset.example || "";
        message.focus();
        updateSummonState();
      }});
    }});

    message.addEventListener("input", updateSummonState);
    screenshot.addEventListener("change", updateImagePreview);
    clearImage.addEventListener("click", () => {{
      screenshot.value = "";
      updateImagePreview();
    }});
    watchFilm.addEventListener("click", openFilmModal);
    closeFilm.addEventListener("click", closeFilmModal);
    filmModal.addEventListener("click", (event) => {{
      if (event.target === filmModal) closeFilmModal();
    }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape" && filmModal.classList.contains("open")) closeFilmModal();
    }});
    updateSummonState();

    async function poll(jobId) {{
      const response = await fetch(`/api/perform/${{jobId}}`);
      if (!response.ok) throw new Error("The theatre lost the playbill.");
      const job = await response.json();
      setLoadingLine(job.line);

      if (job.status === "done") {{
        stopTheatreLines();
        stage.classList.remove("is-performing");
        stage.classList.add("has-result");
        isPerforming = false;
        idleSummonText = "Stage another";
        setSummonText(idleSummonText);
        updateSummonState();
        currentVideoUrl = job.result.video_url;
        film.src = currentVideoUrl;
        watchFilm.disabled = false;
        const resultTitle = job.result.title || "The Court Has Spoken";
        const resultLogline = job.result.logline || "The tiny theatre has finished its work. Press play when you want the drama in full.";
        successTitle.textContent = "The verdict has arrived.";
        successCopy.textContent = resultLogline || "The reel is sealed, the balcony is silent, and the court is prepared to be ridiculous.";
        title.textContent = resultTitle;
        logline.textContent = resultLogline;
        caption.textContent = job.result.caption || "";
        downloads.innerHTML = "";
        (job.result.downloads || []).forEach((item) => {{
          const link = document.createElement("a");
          link.href = item.url;
          link.textContent = item.label;
          link.download = "";
          downloads.appendChild(link);
        }});
        afterword.classList.add("show");
        return;
      }}

      if (job.status === "error") {{
        stopTheatreLines();
        stage.classList.remove("is-performing");
        isPerforming = false;
        idleSummonText = "Try the scene again";
        setSummonText(idleSummonText);
        summon.title = job.error || "The performance collapsed backstage.";
        updateSummonState();
        return;
      }}

      setTimeout(() => poll(jobId).catch(showError), 1400);
    }}

    function showError(error) {{
      stopTheatreLines();
      stage.classList.remove("is-performing");
      isPerforming = false;
      idleSummonText = "Try the scene again";
      setSummonText(idleSummonText);
      summon.title = error.message || error;
      updateSummonState();
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      if (!message.value.trim() && !screenshot.files?.length) {{
        setSummonText("Bring a message first");
        setTimeout(() => {{
          if (!isPerforming) setSummonText(idleSummonText);
        }}, 1600);
        return;
      }}

      isPerforming = true;
      summon.classList.add("is-loading");
      summon.title = "";
      updateSummonState();
      setSummonText("Curtain rising");
      stage.classList.remove("has-result");
      stage.classList.add("is-performing");
      afterword.classList.remove("show");
      currentVideoUrl = "";
      watchFilm.disabled = true;
      closeFilmModal(false);
      film.removeAttribute("src");
      film.load();
      beginTheatreLines();

      const data = new FormData(form);
      data.set("runtime_seconds", DEFAULT_RUNTIME_SECONDS);
      data.set("scene_count", DEFAULT_SCENE_COUNT);
      try {{
        const response = await fetch("/api/perform", {{
          method: "POST",
          body: data
        }});
        if (!response.ok) {{
          const detail = await response.json().catch(() => ({{ detail: "The curtain refused to rise." }}));
          throw new Error(detail.detail || "The curtain refused to rise.");
        }}
        const payload = await response.json();
        poll(payload.job_id).catch(showError);
      }} catch (error) {{
        showError(error);
      }}
    }});
  </script>
</body>
</html>
"""


server = create_server()


if __name__ == "__main__":
    launch_app()
