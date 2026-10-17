#!/usr/bin/env python3
"""YouTube-Video herunterladen, transkribieren und in Wort-Videos schneiden.

Nutzung:
    python cut_youtube_to_word_video.py URL [--model small] [--language de]
                                          [--max-per-word 3]

Jeder Clip wird automatisch verifiziert: Die Fundstelle wird mit Kontext
nachtranskribiert, die Wortgrenzen verfeinert, und das Padding auf die halbe
Sprechpause zum Nachbarwort begrenzt. Nur bestätigte Cuts werden gespeichert.

Danach: `python rate_videos.py` zum Bewerten, `python create_video.py` zum
Zusammensetzen eines Satzes.
"""
import argparse

from wordvideos import cutting, db, download, transcribe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube-Video → verifizierte Wort-Videos (faster-whisper, lokal)"
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
    model = transcribe.build_model(args.model, device=args.device)
    words = transcribe.transcribe_words(video_path, model=model,
                                        language=args.language)
    print(f"{len(words)} Wort-Vorkommen erkannt.")

    ranked = transcribe.rank_candidates(words)
    print(f"Prüfe und schneide Clips für {len(ranked)} Wörter "
          f"(max. {args.max_per_word} pro Wort) …\n")

    total_clips = 0
    for word in sorted(ranked):
        kept = 0
        for approx_start, approx_end, idx in ranked[word]:
            if kept >= args.max_per_word:
                break
            refined = transcribe.refine_with_context(
                model, video_path, word, approx_start, approx_end,
                language=args.language,
            )
            if refined is None:
                continue  # nicht bestätigt → nächste Variante probieren
            start, end = refined

            # Padding durch Nachbarwörter begrenzen (halbe Sprechpause)
            prev_end, next_start = transcribe.neighbor_bounds(words, idx)
            pad_start = min(0.06, max(0.0, (start - prev_end) / 2))
            pad_end = min(0.06, max(0.0, (next_start - end) / 2))

            try:
                file_name, duration = cutting.cut_word_clip(
                    video_path, word, start, end,
                    pad_start=pad_start, pad_end=pad_end,
                )
            except Exception as exc:  # einzelne Clips dürfen nicht alles abbrechen
                print(f"  {word}: FEHLER ({exc})")
                continue
            db.insert_clip(word, file_name, int(duration * 1000), start, end, title)
            kept += 1
            total_clips += 1
            print(f"  ✓ {word}: {file_name} ({duration:.2f}s)")
        if kept == 0:
            print(f"  ✗ {word}: keine bestätigte Variante gefunden")

    s = db.stats()
    print(
        f"\nFertig. {total_clips} verifizierte Clips aus diesem Video; "
        f"insgesamt {s['total']} Clips für {s['words']} Wörter "
        f"in der Datenbank ({s['unrated']} unbewertet)."
    )
    print("Als nächstes: python rate_videos.py")


if __name__ == "__main__":
    main()
