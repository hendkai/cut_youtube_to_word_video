"""Setzt aus Wort-Clips ein Video für einen Satz zusammen (ffmpeg concat)."""
import os
import subprocess

from . import config, db
from .transcribe import normalize_word


def tokenize_sentence(sentence: str) -> list[str]:
    tokens = []
    for raw in sentence.split():
        token = normalize_word(raw)
        if token:
            tokens.append(token)
    return tokens


def create_video_from_sentence(
    sentence: str,
    output_path: str | None = None,
    db_path: str | None = None,
) -> tuple[str | None, list[str]]:
    """Erstellt ein Video aus dem Satz.

    Gibt (Ausgabepfad oder None, fehlende Wörter) zurück. Bevorzugt werden
    Clips mit Bewertung 'gut'; als 'schlecht' bewertete werden nie verwendet.
    """
    tokens = tokenize_sentence(sentence)
    if not tokens:
        return None, []

    clips: list[str] = []
    missing: list[str] = []
    for token in tokens:
        row = db.best_clip_for_word(token, db_path)
        if row is None:
            missing.append(token)
            continue
        path = db.clip_path(row["word"], row["file_name"])
        if not os.path.exists(path):
            missing.append(token)
            continue
        clips.append(path)

    if not clips:
        return None, missing

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    output_path = output_path or os.path.join(config.OUTPUT_DIR, "output_video.mp4")
    list_path = os.path.join(config.OUTPUT_DIR, "concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for path in clips:
            f.write(f"file '{os.path.abspath(path)}'\n")

    # Alle Clips haben dieselben Kodierparameter (libx264/aac) → Stream-Copy.
    # Falls das trotzdem scheitert, fallback mit Neukodierung.
    base_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
    ]
    try:
        subprocess.run(
            base_cmd + ["-c", "copy", "-movflags", "+faststart", output_path],
            check=True,
        )
    except subprocess.CalledProcessError:
        subprocess.run(
            base_cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                        "-c:a", "aac", "-b:a", "128k", output_path],
            check=True,
        )
    return output_path, missing
