"""Zentrale Pfade und Einstellungen des Projekts."""
import os

WORDS_DIR = os.environ.get("WORTVIDEOS_WORDS_DIR", "Wörter")
DOWNLOADS_DIR = os.environ.get("WORTVIDEOS_DOWNLOADS_DIR", "downloads")
OUTPUT_DIR = os.environ.get("WORTVIDEOS_OUTPUT_DIR", "output")
DB_PATH = os.environ.get("WORTVIDEOS_DB", "word_videos.db")

# Bewertungs-Codes in der DB-Spalte `rated`
RATED_UNRATED = -1
RATED_GOOD = 1
RATED_BAD = 0
