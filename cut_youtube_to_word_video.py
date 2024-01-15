from pytube import YouTube
import moviepy.editor as mp
import os
import subprocess
from google.cloud import speech_v1p1beta1 as speech
import re
from moviepy.editor import AudioFileClip
import shutil
from tqdm import tqdm
import json
import sqlite3
import cv2
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox, font
import threading


# SQLite-Datenbank initialisieren
def initialize_db(db_path="word_videos.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Erstellen einer Tabelle, falls sie noch nicht existiert
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY,
            word TEXT,
            file_name TEXT,
            duration_ms INTEGER,
            start_time REAL,
            end_time REAL,
            rated INTEGER DEFAULT -1  -- Geänderte Spalte zur Bewertungskennzeichnung
        )
    """
    )

    conn.commit()
    conn.close()


# Bewertung in der Datenbank speichern
def save_rating(word, file_name, rating, db_path="word_videos.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Setzt die Bewertung auf 1 für gut oder 0 für schlecht
    cursor.execute(
        "UPDATE videos SET rated = ? WHERE word = ? AND file_name = ?",
        (rating, word, file_name),
    )
    conn.commit()
    conn.close()


def is_file_size_within_limit(file_path, size_limit=26214400):  # 26 MB
    file_size = os.path.getsize(file_path)
    return file_size <= size_limit


def safe_folder_name(name):
    """Ersetzt oder entfernt unzulässige Zeichen im Ordnernamen."""
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")


def safe_filename(filename):
    """Ersetzt oder entfernt unzulässige Zeichen im Dateinamen."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "_")


def check_audio_channels(audio_path):
    """
    Überprüft die Anzahl der Audiokanäle in der angegebenen Datei.
    Gibt die Anzahl der Kanäle zurück.
    """
    try:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=channels",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
        channels = int(result.stdout.strip())
        return channels
    except Exception as e:
        print(f"Fehler bei der Überprüfung der Audiokanäle: {e}")
        return None


def download_youtube_video(url, download_folder):
    try:
        yt = YouTube(url)
        stream = (
            yt.streams.filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .desc()
            .first()
        )
        if stream is None:
            raise Exception("Kein geeigneter Stream gefunden.")

        # Erstellen eines sicheren Ordnernamens für das Video
        folder_name = safe_folder_name(yt.title)
        video_folder_path = os.path.join(download_folder, folder_name)

        if not os.path.exists(video_folder_path):
            os.makedirs(video_folder_path)

        # Der Dateiname des Videos sollte nur den Titel und die Erweiterung enthalten
        video_file_name = folder_name + ".mp4"
        video_path = os.path.join(video_folder_path, video_file_name)
        stream.download(filename=video_path)
        return video_path
    except Exception as e:
        print(f"Fehler beim Herunterladen des Videos: {e}")
        return None


def convert_audio_to_mono(video_path):
    try:
        audio_path = os.path.join("downloads", "extracted_audio.wav")
        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-ac",
            "1",  # Setzen auf 1 Kanal (Mono)
            "-ar",
            "44100",  # Abtastrate auf 44100 Hz setzen
            "-y",  # Überschreiben, falls Datei existiert
            audio_path,
        ]
        subprocess.run(command, check=True)
        return audio_path
    except Exception as e:
        print(f"Fehler bei der Audio-Konvertierung: {e}")
        return None


def extract_audio(video_path):
    try:
        audio_path = os.path.join("downloads", "extracted_audio.wav")
        # Verwenden von ffmpeg, um Audio in Mono zu konvertieren
        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-ac",
            "1",  # Setzen auf 1 Kanal (Mono)
            "-ar",
            "44100",  # Abtastrate auf 44100 Hz setzen
            "-y",  # Überschreiben, falls Datei existiert
            audio_path,
        ]
        subprocess.run(command, check=True)
        return audio_path
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        return None


def recognize_speech_from_audio(audio_path, client):
    with open(audio_path, "rb") as audio_file:
        content = audio_file.read()

    config = {
        "language_code": "de-DE",
        "enable_word_time_offsets": True,
        "use_enhanced": False,
    }

    response = client.recognize(config=config, audio={"content": content})

    words_with_timestamps = {}
    for result in response.results:
        for word_info in result.alternatives[0].words:
            word = word_info.word.lower()  # Wörter in Kleinbuchstaben umwandeln
            start_time = word_info.start_time.total_seconds()
            end_time = word_info.end_time.total_seconds()

            word_duration = end_time - start_time
            ideal_duration = 1.0  # Eine geschätzte ideale Dauer für ein Wort

            # Prüfen, ob das Wort bereits erkannt wurde
            if word in words_with_timestamps:
                existing_duration = (
                    words_with_timestamps[word][2] - words_with_timestamps[word][1]
                )
                # Das Wort behalten, dessen Dauer näher an der idealen Dauer liegt
                if abs(word_duration - ideal_duration) < abs(
                    existing_duration - ideal_duration
                ):
                    words_with_timestamps[word] = (word, start_time, end_time)
            else:
                words_with_timestamps[word] = (word, start_time, end_time)

    return list(words_with_timestamps.values())


def cut_video_by_word(video_path, word, start_time, end_time, db_path="word_videos.db"):
    output_folder = "Wörter"
    word_folder = os.path.join(output_folder, word)
    if not os.path.exists(word_folder):
        os.makedirs(word_folder)

    try:
        video = mp.VideoFileClip(video_path).subclip(start_time, end_time)
        video_duration = video.duration  # Dauer des Videos in Sekunden

        # Erstellen des Videodateinamens
        video_file_name = f"{word}_{len(os.listdir(word_folder))}.mp4"
        output_path = os.path.join(word_folder, video_file_name)
        video.write_videofile(output_path)

        # Speichern der Videoinformationen in der SQLite-Datenbank
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO videos (word, file_name, duration_ms, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """,
            (word, video_file_name, video_duration * 1000, start_time, end_time),
        )
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Fehler beim Schneiden des Wortes '{word}': {e}")


def get_audio_length(audio_path):
    """
    Ermittelt die Länge der Audiodatei in Sekunden.
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    duration = float(result.stdout)
    return duration / 60  # Umwandlung in Minuten


def estimate_costs(audio_length, price_per_minute=0.016, num_words=0):
    """
    Schätzt die Kosten für die Verarbeitung der Audiodatei basierend auf Google Cloud Speech-to-Text.
    :param audio_length: Länge der Audiodatei in Minuten.
    :param price_per_minute: Kosten pro Minute für Google Cloud Speech-to-Text.
    :param num_words: Anzahl der zu überprüfenden Wörter.
    :return: Geschätzte Gesamtkosten.
    """
    transcription_cost = audio_length * price_per_minute
    verification_cost = (
        num_words * price_per_minute
    )  # Annahme: Gleicher Preis pro Wort wie pro Minute
    total_cost = transcription_cost + verification_cost
    return total_cost


def confirm_costs(costs_text):
    print(costs_text)
    user_input = input("Sind Sie damit einverstanden? (ja/nein): ")
    return user_input.lower() == "ja"


def split_audio_mono_ffmpeg(file_path, segment_length=50):
    total_duration_command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(total_duration_command, stdout=subprocess.PIPE, text=True)
    total_duration = float(result.stdout.strip())

    segments = []
    for start in range(0, int(total_duration), segment_length):
        end = min(start + segment_length, total_duration)
        segment_file_path = f"downloads/segment_{start}_{end}.wav"
        command = [
            "ffmpeg",
            "-i",
            file_path,
            "-ss",
            str(start),
            "-to",
            str(end),
            "-ac",
            "1",  # Setzen auf 1 Kanal (Mono)
            segment_file_path,
        ]
        subprocess.run(command, check=True)
        segments.append(segment_file_path)

    return segments


def transcribe_video_with_speech_to_text(video_path, speech_client):
    """
    Transkribiert das gesprochene Wort in einem Video mithilfe von Google Cloud Speech-to-Text.
    """
    # Extrahiere Audio aus dem Video
    audio_path = extract_audio(video_path)
    if audio_path is None:
        print("Fehler beim Extrahieren des Audios.")
        return None

    # Transkribiere das Audio
    words_with_timestamps = recognize_speech_from_audio(audio_path, speech_client)

    return words_with_timestamps


def verify_and_sort_videos(word, base_folder="Wörter"):
    """
    Überprüft, ob das Wort in den Videos korrekt ist und sortiert sie entsprechend.
    """
    word_folder = os.path.join(
        base_folder, word
    )  # Definiert den Pfad zum Ordner des Wortes

    checked_folder = os.path.join(base_folder, "geprüft", word)
    faulty_folder = os.path.join(base_folder, "fehlerhaft", word)

    if not os.path.exists(word_folder):
        print(f"Kein Ordner für das Wort '{word}' gefunden.")
        return

    for video_file in os.listdir(word_folder):
        video_path = os.path.join(word_folder, video_file)
        transcribed_word = transcribe_video_with_speech_to_text(
            video_path, speech_client
        )

        if transcribed_word and transcribed_word.lower() == word.lower():
            target_folder = checked_folder
        else:
            target_folder = faulty_folder

        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        shutil.move(video_path, os.path.join(target_folder, video_file))


def estimate_duration(audio_length, processing_speed=1.0):
    """
    Schätzt die Dauer der Bearbeitung basierend auf der Audio-Länge und der Verarbeitungsgeschwindigkeit.
    :param audio_length: Länge der Audiodatei in Minuten.
    :param processing_speed: Geschätzte Verarbeitungsgeschwindigkeit in Minuten pro Minute.
    :return: Geschätzte Dauer der Bearbeitung in Minuten.
    """
    estimated_duration = audio_length * processing_speed
    return estimated_duration


def process_audio_for_clarity(audio_path):
    processed_audio_path = audio_path.replace(".wav", "_processed.wav")
    command = [
        "ffmpeg",
        "-i",
        audio_path,
        "-af",
        "arnndn=m=rnnnoise,compand,eq=equalizer=f=8000:t=h:width=200:g=-10",
        "-ar",
        "44100",
        "-ac",
        "1",
        processed_audio_path,
    ]
    subprocess.run(command, check=True)
    return processed_audio_path


def transcribe_and_verify_video(video_path, word, client):
    """Transkribiert das Video und überprüft, ob das spezifische Wort enthalten ist."""
    audio_path = extract_audio(video_path)
    if audio_path is None:
        print("Fehler beim Extrahieren des Audios.")
        return False

    words = recognize_speech_from_audio(audio_path, client)
    return any(w.lower() == word.lower() for w, _, _ in words)


def delete_video_and_db_entry(word, file_name, db_path="word_videos.db"):
    """Löscht das Video und den entsprechenden Datenbankeintrag."""
    video_path = os.path.join("Wörter", word, file_name)

    # Überprüfen, ob die Videodatei existiert
    if os.path.exists(video_path):
        # Lösche die Videodatei
        os.remove(video_path)
        print(f"Video {video_path} wurde gelöscht.")

        # Verbindung zur SQLite-Datenbank herstellen
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Lösche den entsprechenden Eintrag aus der Datenbank
        cursor.execute(
            "DELETE FROM videos WHERE word = ? AND file_name = ?", (word, file_name)
        )
        conn.commit()
        conn.close()
        print(f"Eintrag für {word} in der Datenbank gelöscht.")
    else:
        print(f"Video {video_path} nicht gefunden.")


# Funktion zur Bewertung eines Videos
def rate_and_get_rating(video_path, word, video_file):
    # Hier füge den Code zur Anzeige des Videos und zur Ermittlung der Bewertung ein
    # Die Bewertung kann auf verschiedene Weisen erfolgen, z.B. durch Benutzereingabe oder automatische Analyse

    # Beispiel: Bewertung als Platzhalter
    rating = 5  # Annahme: Das Video erhält eine Bewertung von 5

    return rating


# Funktion zur Überprüfung, ob ein Video bereits bewertet wurde
def is_video_rated(word, video_file, db_path="word_videos.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rated FROM videos WHERE word = ? AND file_name = ?", (word, video_file)
    )
    result = cursor.fetchone()
    conn.close()

    if result is not None:
        return bool(result[0])  # Gibt True zurück, wenn das Video bewertet wurde
    else:
        return False  # Gibt False zurück, wenn das Video nicht bewertet wurde oder nicht in der Datenbank existiert


# Funktion zum Speichern der Bewertung in der Datenbank
def save_rating(word, video_file, rating, db_path="word_videos.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE videos SET rated = ? WHERE word = ? AND file_name = ?",
        (rating, word, video_file),
    )
    conn.commit()
    conn.close()


def process_videos():
    # Hier füge den Code zum Herunterladen, Zuschneiden und Extrahieren von Videos ein

    # Dann starte die Schleife zur Bewertung der Videos
    for word_folder, _, video_files in os.walk("Wörter"):
        for video_file in video_files:
            word = os.path.basename(word_folder)
            video_path = os.path.join(word_folder, video_file)

            # Überprüfen, ob das Video bereits bewertet wurde
            if not is_video_rated(word, video_file):
                # Video anzeigen und bewerten
                rating = rate_and_get_rating(video_path, word, video_file)

                # Bewertung in der Datenbank speichern
                save_rating(word, video_file, rating)


def play_video(video_path, label):
    cap = cv2.VideoCapture(video_path)

    def update_frame():
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            label.imgtk = imgtk
            label.configure(image=imgtk)
            label.after(20, update_frame)
        else:
            label.configure(image="")

    update_frame()


def play_video_in_vlc(video_path):
    def run_vlc():
        try:
            subprocess.Popen(["cvlc", video_path])
        except Exception as e:
            print(f"Fehler beim Starten von VLC: {e}")

    thread = threading.Thread(target=run_vlc)
    thread.start()


def rate_video(word, video_path):
    # Erstellen eines neuen Fensters
    window = tk.Tk()
    window.title(f"Bewerte das Wort: {word}")

    # Überschrift für das Wort
    heading_font = font.Font(family="Helvetica", size=16, weight="bold")
    heading_label = tk.Label(
        window, text=f"Wort zur Bewertung: {word}", font=heading_font
    )
    heading_label.pack()

    # Video in VLC abspielen
    tk.Button(
        window, text="Video abspielen", command=lambda: play_video_in_vlc(video_path)
    ).pack()

    # Bewertungsbuttons
    def submit_rating(rating):
        print(f"Bewertung für {word} ({video_path}): {rating}")
        # Speichere die Bewertung in der Datenbank
        save_rating(word, os.path.basename(video_path), rating)
        window.destroy()

    tk.Button(window, text="Gut", command=lambda: submit_rating(1)).pack()
    tk.Button(window, text="Schlecht", command=lambda: submit_rating(0)).pack()

    window.mainloop()  # Dies blockiert die Ausführung, bis das Fenster geschlossen wird


def main():
    url = "https://www.youtube.com/shorts/pes9pXYZTUI"
    download_folder = "downloads"
    try:
        video_path = download_youtube_video(url, download_folder)
        if video_path is None or not os.path.exists(video_path):
            print("Fehler beim Herunterladen oder Finden des Videos.")
            return

        audio_path = convert_audio_to_mono(video_path)
        if audio_path is None or not os.path.exists(audio_path):
            print(
                "Fehler beim Konvertieren des Audios oder die Audiodatei existiert nicht."
            )
            return

        channels = check_audio_channels(audio_path)
        if channels != 1:
            print(f"Die Audiodatei ist nicht Mono, sie hat {channels} Kanäle.")
            return
        else:
            print("Die Audiodatei ist Mono.")

        audio_length = get_audio_length(audio_path)
        estimated_costs = estimate_costs(audio_length)
        estimated_duration = estimate_duration(audio_length)
        if not confirm_costs(
            f"Die geschätzten Kosten für die Bearbeitung betragen {estimated_costs:.2f} Euro und die geschätzte Dauer beträgt ca. {estimated_duration:.2f} Minuten."
        ):
            print("Kosten wurden nicht bestätigt. Verarbeitung abgebrochen.")
            return

        initialize_db()

        segment_paths = split_audio_mono_ffmpeg(audio_path, segment_length=50)
        speech_client = speech.SpeechClient()

        num_segments = len(segment_paths)
        for i, segment_path in enumerate(segment_paths):
            print(f"Verarbeite Segment {i+1}/{num_segments}: {segment_path}")
            words_with_timestamps = recognize_speech_from_audio(
                segment_path, speech_client
            )

            for word, start_time, end_time in words_with_timestamps:
                try:
                    cut_video_by_word(video_path, word, start_time, end_time)
                    video_file_path = os.path.join("Wörter", word, f"{word}.mp4")
                    if os.path.exists(video_file_path):
                        if transcribe_and_verify_video(
                            video_file_path, word, speech_client
                        ):
                            print(f"Video für das Wort '{word}' bestätigt.")
                        else:
                            print(
                                f"Video für das Wort '{word}' enthält das Wort nicht. Wird entfernt."
                            )
                            delete_video_and_db_entry(word, f"{word}.mp4")
                    else:
                        print(f"Video für das Wort '{word}' nicht gefunden.")
                except Exception as e:
                    print(
                        f"Fehler beim Schneiden oder Überprüfen des Videos für das Wort '{word}': {e}"
                    )
                    continue

        base_folder = "Wörter"
        for word_folder in os.listdir(base_folder):
            word_path = os.path.join(base_folder, word_folder)
            if os.path.isdir(word_path):
                for video_file in os.listdir(word_path):
                    video_file_path = os.path.join(word_path, video_file)
                    rate_video(word_folder, video_file_path)

    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    main()
