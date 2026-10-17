#!/usr/bin/env python3
"""Tkinter-GUI zum Bewerten der Wort-Videos.

Nutzung:
    python rate_videos.py

Jeder noch unbewertete Clip wird angezeigt; per Knopf (oder Taste g/s)
wird er als gut oder schlecht bewertet. Die Bewertung landet in der
SQLite-Datenbank; als 'schlecht' bewertete Clips werden beim
Zusammensetzen nie verwendet.
"""
import os
import subprocess
import tkinter as tk
from tkinter import ttk

from wordvideos import config, db


class RatingApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Wort-Videos bewerten")
        self.minsize(420, 300)

        db.init_db()
        self.clips = db.unrated_clips()
        self.index = 0

        self.heading = ttk.Label(self, font=("", 14, "bold"))
        self.heading.pack(pady=(12, 4))

        self.info = ttk.Label(self)
        self.info.pack()

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=8)
        ttk.Button(button_frame, text="Abspielen (Leertaste)",
                   command=self.play).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Gut (g)",
                   command=self.rate_good).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Schlecht (s)",
                   command=self.rate_bad).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Überspringen (→)",
                   command=self.next_clip).pack(side="left", padx=4)

        self.progress = ttk.Label(self)
        self.progress.pack(pady=(4, 12))

        self.bind("<space>", lambda _e: self.play())
        self.bind("g", lambda _e: self.rate_good())
        self.bind("s", lambda _e: self.rate_bad())
        self.bind("<Right>", lambda _e: self.next_clip())

        self.show_clip()

    # ---------- Anzeige ----------

    def current(self):
        if 0 <= self.index < len(self.clips):
            return self.clips[self.index]
        return None

    def show_clip(self) -> None:
        clip = self.current()
        s = db.stats()
        if clip is None:
            self.heading.config(text="Alles bewertet! 🎉")
            self.info.config(text="")
            self.progress.config(
                text=f"{s['total']} Clips: {s['good']} gut · "
                     f"{s['bad']} schlecht · {s['unrated']} unbewertet"
            )
            return
        duration_ms = clip["duration_ms"] or 0
        self.heading.config(text=f"Wort: {clip['word']}")
        self.info.config(
            text=f"{clip['file_name']} · {duration_ms / 1000:.2f}s · "
                 f"Quelle: {clip['source_title'] or '?'}"
        )
        self.progress.config(
            text=f"Clip {self.index + 1} / {len(self.clips)} · "
                 f"{s['good']} gut · {s['bad']} schlecht"
        )

    # ---------- Aktionen ----------

    def play(self) -> None:
        clip = self.current()
        if clip is None:
            return
        path = db.clip_path(clip["word"], clip["file_name"])
        if os.path.exists(path):
            subprocess.Popen(["xdg-open", path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _rate(self, rating: int) -> None:
        clip = self.current()
        if clip is None:
            return
        db.set_rating(clip["id"], rating)
        self.next_clip()

    def rate_good(self) -> None:
        self._rate(config.RATED_GOOD)

    def rate_bad(self) -> None:
        self._rate(config.RATED_BAD)

    def next_clip(self) -> None:
        if self.index < len(self.clips):
            self.index += 1
        self.show_clip()


def main() -> None:
    RatingApp().mainloop()


if __name__ == "__main__":
    main()
