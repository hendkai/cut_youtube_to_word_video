"""Video-Download via yt-dlp."""
import os

from yt_dlp import YoutubeDL

from . import config


def download_video(
    url: str,
    folder: str | None = None,
    max_height: int = 1080,
) -> tuple[str, str]:
    """Lädt das Video als MP4 (max. `max_height`) herunter.

    Gibt (Dateipfad, Titel) zurück.
    """
    folder = folder or config.DOWNLOADS_DIR
    os.makedirs(folder, exist_ok=True)

    opts = {
        "format": (
            f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]"
            f"/b[height<={max_height}][ext=mp4]/b[ext=mp4]/b"
        ),
        "outtmpl": os.path.join(folder, "%(title).80B.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError(f"Download fehlgeschlagen: {url}")
        title = info.get("title") or "unbekannt"
        path = None
        for entry in info.get("requested_downloads", []):
            path = entry.get("filepath")
            if path:
                break
        if not path:
            # Fallback: neueste Datei im Download-Ordner
            candidates = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.endswith(".mp4")
            ]
            if not candidates:
                raise RuntimeError("Download fertig, aber keine MP4-Datei gefunden.")
            path = max(candidates, key=os.path.getmtime)

    if not os.path.exists(path):
        raise RuntimeError(f"Heruntergeladene Datei fehlt: {path}")
    return path, title
