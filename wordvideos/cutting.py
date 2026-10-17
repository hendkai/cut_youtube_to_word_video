"""Schneidet Wort-Clips aus dem Quellvideo (ffmpeg, neu kodiert = exakt)."""
import os
import subprocess

from . import config


def cut_word_clip(
    source_path: str,
    word: str,
    start: float,
    end: float,
    pad_start: float = 0.06,
    pad_end: float = 0.06,
    words_dir: str | None = None,
) -> tuple[str, float]:
    """Schneidet [start, end] (+ individuelle Padding-Begrenzung) aus dem
    Quellvideo. Die Aufrufer begrenzen pad_start/pad_end auf die halbe
    Sprechpause zum Nachbarwort, damit kein Wortschwanz mit in den Clip kommt.

    Legt den Clip unter <words_dir>/<wort>/<wort>_NNN.mp4 ab und gibt
    (Dateiname, Clip-Dauer in Sekunden) zurück.
    """
    words_dir = words_dir or config.WORDS_DIR
    start = max(0.0, start - pad_start)
    end = end + pad_end
    duration = end - start
    if duration <= 0:
        raise ValueError(f"Ungültiger Zeitbereich für '{word}': {start:.2f}–{end:.2f}")

    word_folder = os.path.join(words_dir, word)
    os.makedirs(word_folder, exist_ok=True)

    prefix = f"{word}_"
    existing = [f for f in os.listdir(word_folder) if f.startswith(prefix)]
    file_name = f"{word}_{len(existing):03d}.mp4"
    output_path = os.path.join(word_folder, file_name)

    # -ss vor -i (schnelles Suchen) + Neukodierung = frame-genau.
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-i", source_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(command, check=True)
    return file_name, duration
