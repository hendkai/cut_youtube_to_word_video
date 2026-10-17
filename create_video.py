#!/usr/bin/env python3
"""Video aus einem Satz zusammensetzen.

Nutzung:
    python create_video.py "Hallo Welt" [-o ausgabe.mp4]

Ohne Satz-Argument: verfügbare Wörter anzeigen und interaktiv fragen.
Bevorzugt werden als 'gut' bewertete Clips; 'schlecht' bewertete werden
übersprungen.
"""
import argparse
import os

from wordvideos import config, db
from wordvideos.assemble import create_video_from_sentence


def list_available_words() -> None:
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT word,
                   COUNT(*) AS total,
                   SUM(rated = ?) AS good,
                   SUM(rated = ?) AS bad
            FROM videos
            GROUP BY word
            ORDER BY word
            """,
            (config.RATED_GOOD, config.RATED_BAD),
        ).fetchall()
    if not rows:
        print("Keine Wort-Videos in der Datenbank. "
              "Zuerst cut_youtube_to_word_video.py ausführen.")
        return
    print(f"{len(rows)} verfügbare Wörter:")
    for row in rows:
        marks = []
        if row["good"]:
            marks.append(f"{row['good']}x gut")
        if row["bad"]:
            marks.append(f"{row['bad']}x schlecht")
        if row["total"] - (row["good"] or 0) - (row["bad"] or 0) > 0:
            marks.append("unbewertet")
        suffix = f" ({', '.join(marks)})" if marks else ""
        print(f"  {row['word']}{suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Satz → Wort-Video")
    parser.add_argument("sentence", nargs="?", help="Der zusammensetzende Satz")
    parser.add_argument("-o", "--output", help="Ausgabedatei (Standard: output/output_video.mp4)")
    args = parser.parse_args()

    db.init_db()
    list_available_words()

    sentence = args.sentence or input("\nGib einen Satz ein: ").strip()
    if not sentence:
        print("Leerer Satz — nichts zu tun.")
        return

    output_path, missing = create_video_from_sentence(sentence, args.output)

    if missing:
        print(f"\nKein Video gefunden für: {', '.join(missing)}")
    if output_path:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"\nVideo erstellt: {output_path} ({size_mb:.1f} MB)")
    elif not missing:
        print("\nKeine bekannten Wörter im Satz.")


if __name__ == "__main__":
    main()
