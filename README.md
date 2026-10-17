# 🎬 Wort-Videos aus YouTube

YouTube-Videos herunterladen, transkribieren, in **einzelne Wort-Videos** schneiden, per GUI bewerten und aus einem beliebigen Satz wieder zu einem Video zusammensetzen.

Vollständig **lokal**: Transkription via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper) — keine Cloud-API, keine Kosten pro Minute.

## 🚀 Setup

```bash
uv venv --python 3.12 .venv        # oder: python3.12 -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Voraussetzungen: Python 3.10+, `ffmpeg`/`ffprobe` im PATH (Arch: `pacman -S ffmpeg`).

## 📋 Workflow

### 1. Video verarbeiten

```bash
.venv/bin/python cut_youtube_to_word_video.py "https://www.youtube.com/watch?v=..." \
    --model small --language de --max-per-word 3
```

- Download via **yt-dlp** (max. 1080p, MP4)
- Transkription mit **Wort-Zeitstempeln** (Zeitstempel beziehen sich auf das gesamte Video → Schnitte stimmen exakt)
- Pro Wort bis `--max-per-word` Clips, bevorzugt mit einer Dauer nahe 0,6 s
- Clips landen in `Wörter/<wort>/<wort>_NNN.mp4`, der Index in `word_videos.db` (SQLite)

Whisper-Modelle: `tiny` / `base` / `small` / `medium` / `large-v3` — je größer, desto genauer und langsamer. Das Modell wird beim ersten Start automatisch heruntergeladen.

### 2. Clips bewerten (Tkinter-GUI)

```bash
.venv/bin/python rate_videos.py
```

Tastatur: `Leertaste` = abspielen (System-Player), `g` = gut, `s` = schlecht, `→` = überspringen.

### 3. Satz → Video

```bash
.venv/bin/python create_video.py "hallo welt"            # oder interaktiv ohne Argument
```

Bevorzugt werden als **gut** bewertete Clips; als **schlecht** bewertete werden nie verwendet. Fehlende Wörter werden gemeldet. Ausgabe: `output/output_video.mp4`.

## 📁 Struktur

```
wordvideos/            Kernmodul
  config.py            Pfade & Bewertungs-Codes
  db.py                SQLite-Index (Wörter, Clips, Bewertungen)
  download.py          yt-dlp-Download
  transcribe.py        faster-whisper + Wort-Auswahl
  cutting.py           ffmpeg-Schnitt (frame-genau, neu kodiert)
  assemble.py          Satz → Video (ffmpeg concat)
cut_youtube_to_word_video.py   CLI: Video → Wort-Clips
rate_videos.py                 Tkinter-Bewertungs-GUI
create_video.py                Satz → Video
```

Pfade lassen sich per Umgebungsvariablen überschreiben: `WORTVIDEOS_WORDS_DIR`, `WORTVIDEOS_DOWNLOADS_DIR`, `WORTVIDEOS_OUTPUT_DIR`, `WORTVIDEOS_DB`.

## 🗄️ Datenbank

Tabelle `videos`: `word`, `file_name`, `duration_ms`, `start_time`, `end_time`, `rated` (`-1` unbewertet, `1` gut, `0` schlecht), `source_title`.

## 🔒 Lizenz

Keine Open-Source-Lizenz. Alle Rechte vorbehalten; Nutzung, Vervielfältigung oder Verbreitung des Codes nur mit ausdrücklicher Genehmigung des Autors.

## 🛣️ Roadmap

1. Automatische Qualitätsbewertung der Wort-Clips (ML-Modell statt manueller GUI-Bewertung)
2. Wort-Varianten aus mehreren Quellvideos deduplizieren
3. Web-/TUI-Oberfläche für Satz → Video mit Live-Vorschau

---

⚠️ Nur für Videos verwenden, deren Nutzung (Lizenz/Fair Use) dies erlaubt.
