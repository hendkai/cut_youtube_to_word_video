"""Wort-Videos-Projekt: YouTube → Wort-Clips → Bewertung → Satz-Video."""

import os

# HuggingFace-Xet-CDN wird vom lokalen (Tailscale-)DNS blockiert –
# normaler HTTPS-Download erzwingen. Muss vor dem Import von
# faster_whisper/huggingface_hub gesetzt sein (passiert hier automatisch).
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
