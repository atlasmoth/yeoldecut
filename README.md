---
title: YeOldeCut
emoji: 🎬
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: "6.18.0"
app_file: app.py
python_version: "3.12"
pinned: false
suggested_hardware: a10g-small
short_description: Turn rejection texts into dramatic medieval roast films.
tags:
  - build-small-hackathon
  - gradio
  - text-to-video
  - open-weights
  - minicpm
  - track:wood
  - sponsor:openai
  - sponsor:openbmb
  - achievement:offgrid
  - achievement:offbrand
  - achievement:demo
---

# YeOldeCut

Turn painful rejection texts into dramatic medieval roast films.

YeOldeCut takes a breakup, job rejection, investor pass, ghosting message, or screenshot and turns it into a short MP4: faux-medieval script, generated scene art, narrated voiceover, background score, subtitles, title card, final card, and a share caption.

## Demo Video

<video src="https://res.cloudinary.com/dzhtwka6d/video/upload/v1781563099/YeOldeCut_Demo_q1pv5e.mp4" controls width="100%"></video>

[Watch the demo video](https://res.cloudinary.com/dzhtwka6d/video/upload/v1781563099/YeOldeCut_Demo_q1pv5e.mp4)

## Launch Post

[Read the launch post on X](https://x.com/c__osuji/status/2066660708855497177)

## Build Small Positioning

- Track: Thousand Token Wood
- Core output: downloadable MP4 for demos and social sharing
- Small/open model stack: Gemma director model, FLUX.2 Klein 4B scene generation, OpenBMB VoxCPM2 narration from the MiniCPM family, and MusicGen background score
- Sponsor hooks: OpenBMB/MiniCPM-family narration, Black Forest Labs image generation, and Codex-attributed development for the OpenAI track
- Off-grid note: the app does not call hosted model APIs at runtime; generation runs through downloaded open-weight models in the Space process.

## Local Development

```bash
uv sync
uv run python app.py
```

The app writes generated artifacts under `outputs/<run-id>/`.
