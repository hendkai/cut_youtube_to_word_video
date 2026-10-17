"""Transkription mit Wort-Zeitstempeln via faster-whisper (lokal, kostenlos)."""
import os
import re
import subprocess
import tempfile

from faster_whisper import WhisperModel

# Ein Wort muss mindestens einen Buchstaben enthalten (Umlaute inklusive).
_LETTER_RE = re.compile(r"[a-zäöüß]")
_STRIP_CHARS = ".,!?;:\"'()[]{}<>|/\\…-–—„“”«»*#$§%&_=~^°+@"


def normalize_word(raw: str) -> str | None:
    """Macht ein erkanntes Token zu einem normalisierten Wort oder None."""
    word = raw.strip().lower().strip(_STRIP_CHARS)
    if not word or not _LETTER_RE.search(word):
        return None
    if any(ch.isdigit() for ch in word):
        return None
    return word


def words_match(a: str, b: str) -> bool:
    """Grob-Vergleich erkannter vs. erwarteter Wortform (inkl. Flexionsformen)."""
    return a == b or (len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5])


def build_model(
    model_size: str = "small", device: str = "auto", compute_type: str = "auto"
) -> WhisperModel:
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe_words(
    media_path: str,
    model: WhisperModel | None = None,
    model_size: str = "small",
    language: str = "de",
    device: str = "auto",
    compute_type: str = "auto",
) -> list[tuple[str, float, float]]:
    """Transkribiert Audio/Video und gibt (Wort, Start_s, Ende_s) in
    Sprechreihenfolge zurück.

    Die Zeitstempel beziehen sich auf die komplette Mediendatei, sodass
    die Schnittzeiten direkt zum Quellvideo passen.
    """
    model = model or build_model(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        media_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
    )

    words: list[tuple[str, float, float]] = []
    for segment in segments:
        for w in segment.words or []:
            token = normalize_word(w.word)
            if token:
                words.append((token, float(w.start), float(w.end)))
    return words


def rank_candidates(
    words: list[tuple[str, float, float]],
    max_attempts: int = 5,
    min_duration: float = 0.15,
    ideal_duration: float = 0.6,
) -> dict[str, list[tuple[float, float, int]]]:
    """Sortiert pro Wort die Kandidaten-Vorkommen nach "schöner" Dauer.

    Gibt {wort: [(start, ende, index_in_wortsliste)]} zurück; der Index wird
    für die Nachbarwörter (Padding-Begrenzung) gebraucht.
    """
    by_word: dict[str, list[tuple[float, float, int]]] = {}
    for idx, (word, start, end) in enumerate(words):
        if end - start >= min_duration:
            by_word.setdefault(word, []).append((start, end, idx))
    for occurrences in by_word.values():
        occurrences.sort(key=lambda t: abs((t[1] - t[0]) - ideal_duration))
    return {w: occ[:max_attempts] for w, occ in by_word.items()}


def neighbor_bounds(
    words: list[tuple[str, float, float]], idx: int
) -> tuple[float, float]:
    """(Ende_des_vorherigen_Worts, Start_des_nächsten_Worts).

    Der Index bezieht sich auf die eigene Kandidatenstelle, damit das
    Padding nie ins Nachbarwort hineinreicht."""
    prev_end = words[idx - 1][2] if idx > 0 else float("inf")
    next_start = words[idx + 1][1] if idx + 1 < len(words) else float("inf")
    return prev_end, next_start


def refine_with_context(
    model: WhisperModel,
    media_path: str,
    word: str,
    approx_start: float,
    approx_end: float,
    language: str = "de",
    window: float = 1.5,
    tolerance: float = 0.75,
) -> tuple[float, float] | None:
    """Transkribiert die Stelle mit ±window Sekunden Kontext nach.

    Mit Kontext erkennt Whisper Wortgrenzen deutlich zuverlässiger als bei
    isolierten Mini-Clips. Gibt die verfeinerten (start, ende) des Zielworts
    zurück — oder None, wenn das Wort dort nicht bestätigt wird.
    """
    seg_start = max(0.0, approx_start - window)
    seg_end = approx_end + window
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "context.wav")
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{seg_start:.3f}", "-t", f"{seg_end - seg_start:.3f}",
                "-i", media_path, "-ar", "16000", "-ac", "1", wav,
            ],
            check=True,
        )
        segments, _info = model.transcribe(
            wav, language=language, word_timestamps=True, beam_size=5,
            condition_on_previous_text=False,
        )
        for segment in segments:
            for w in segment.words or []:
                token = normalize_word(w.word)
                if not token or not words_match(token, word):
                    continue
                start = seg_start + float(w.start)
                end = seg_start + float(w.end)
                if abs(start - approx_start) <= tolerance and 0.1 < end - start < 4.0:
                    return start, end
    return None
