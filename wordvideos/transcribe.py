"""Transkription mit Wort-Zeitstempeln via faster-whisper (lokal, kostenlos)."""
import re

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


def transcribe_words(
    media_path: str,
    model_size: str = "small",
    language: str = "de",
    device: str = "auto",
    compute_type: str = "auto",
) -> list[tuple[str, float, float]]:
    """Transkribiert Audio/Video und gibt (Wort, Start_s, Ende_s) zurück.

    Die Zeitstempel beziehen sich auf die komplette Mediendatei —
    anders als im alten Code wird nicht pro Segment verrechnet, sodass
    die Schnittzeiten direkt mit dem Quellvideo übereinstimmen.
    """
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
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


def select_best_occurrences(
    words: list[tuple[str, float, float]],
    max_per_word: int = 3,
    min_duration: float = 0.15,
    ideal_duration: float = 0.6,
) -> list[tuple[str, float, float]]:
    """Wählt pro Wort die Vorkommen mit der "schönsten" Dauer aus."""
    by_word: dict[str, list[tuple[float, float]]] = {}
    for word, start, end in words:
        if end - start >= min_duration:
            by_word.setdefault(word, []).append((start, end))

    selected: list[tuple[str, float, float]] = []
    for word, occurrences in sorted(by_word.items()):
        occurrences.sort(key=lambda se: abs((se[1] - se[0]) - ideal_duration))
        for start, end in occurrences[:max_per_word]:
            selected.append((word, start, end))
    return selected
