#!/usr/bin/env python3
"""YouTube-Video herunterladen, transkribieren und in Wort-Videos schneiden.

Nutzung:
    python cut_youtube_to_word_video.py URL [--model small] [--language de]
                                          [--max-per-word 3]

Danach: `python rate_videos.py` zum Bewerten, `python create_video.py` zum
Zusammensetzen eines Satzes.
"""
import argparse

from wordvideos import config, cutting, db, download, transcribe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube-Video → Wort-Videos (faster-whisper, lokal)"
    )
    parser.add_argument("url", help="YouTube-URL (oder ytsearch…)")
    parser.add_argument("--model", default="small",
                        help="Whisper-Modell (tiny/base/small/medium/large-v3)")
    parser.add_argument("--language", default="de", help="Sprachcode (Standard: de)")
    parser.add_argument("--max-per-word", type=int, default=3,
                        help="Max. Clips pro Wort (Standard: 3)")
    parser.add_argument("--device", default="auto", help="cpu/cuda/auto")
    args = parser.parse_args()

    db.init_db()

    print(f"Lade Video herunter: {args.url}")
    video_path, title = download.download_video(args.url)
    print(f"Video: {title}\n      {video_path}")

    print(f"Transkribiere (Modell '{args.model}', Sprache '{args.language}') …")
    words = transcribe.transcribe_words(
        video_path, model_size=args.model, language=args.language,
        device=args.device,
    )
    print(f"{len(words)} Wort-Vorkommen erkannt.")

    selected = transcribe.select_best_occurrences(words, args.max_per_word)
    unique_words = len({word for word, _, _ in selected})
    print(f"Schneide {len(selected)} Clips für {unique_words} Wörter …\n")

    for i, (word, start, end) in enumerate(selected, 1):
        try:
            file_name, duration = cutting.cut_word_clip(video_path, word, start, end)
        except Exception as exc:  # einzelne Clips dürfen nicht alles abbrechen
            print(f"[{i}/{len(selected)}] {word}: FEHLER ({exc})")
            continue
        db.insert_clip(word, file_name, int(duration * 1000), start, end, title)
        print(f"[{i}/{len(selected)}] {word}: {file_name} ({duration:.2f}s)")

    s = db.stats()
    print(
        f"\nFertig. Insgesamt {s['total']} Clips für {s['words']} Wörter "
        f"in der Datenbank ({s['unrated']} unbewertet)."
    )
    print("Als nächstes: python rate_videos.py")


if __name__ == "__main__":
    main()
