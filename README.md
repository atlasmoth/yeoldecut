---
title: YeOldeCut
sdk: gradio
app_file: app.py
pinned: false
tags:
  - build-small-hackathon
  - gradio
  - text-to-video
  - open-weights
---

# YeOldeCut

Turn painful rejection texts into dramatic medieval roast films.

YeOldeCut takes a breakup, job rejection, investor pass, ghosting message, or screenshot and turns it into a short MP4: faux-medieval script, generated scene art, narrated voiceover, background score, subtitles, title card, final card, and a share caption.

## Build Small Positioning

- Track: Thousand Token Wood
- Core output: downloadable MP4 for demos and social sharing
- Small/open model stack: Gemma director model, FLUX.2 Klein 4B scene generation, VoxCPM2 narration, and MusicGen background score
- Sponsor hooks: Black Forest Labs for image generation, OpenBMB for narration, and Codex-attributed development for the OpenAI track

## Local Development

```bash
/Users/atlasmoth/.local/bin/uv sync
/Users/atlasmoth/.local/bin/uv run python app.py
```

The app writes generated artifacts under `outputs/<run-id>/`.
