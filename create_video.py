import os
import moviepy.editor as mp

def list_available_words():
    input_dir = "Wörter"  # Pfad zum Hauptordner

    # Überprüfen, ob es verfügbare Wörter (Unterordner) mit Videodateien gibt
    available_words = []
    for folder in os.listdir(input_dir):
        folder_path = os.path.join(input_dir, folder)
        if os.path.isdir(folder_path):
            video_files = [f for f in os.listdir(folder_path) if f.endswith('.mp4')]
            if video_files:
                available_words.append(folder)

    if available_words:
        print("Verfügbare Wörter mit Videodateien:")
        for word in available_words:
            print(word)
    else:
        print("Es wurden keine verfügbaren Wörter mit Videodateien gefunden.")

def create_video_from_sentence(sentence):
    input_dir = "Wörter"  # Pfad zum Hauptordner
    output_dir = "output"  # Ausgabeordner

    # Tokenisieren Sie den Satz in Wörter
    words = sentence.split()

    videos = []
    for word in words:
        word_folder = os.path.join(input_dir, word)
        video_files = [f for f in os.listdir(word_folder) if f.endswith('.mp4')]
        video_files.sort()

        if video_files:
            # Nehmen Sie das erste Video im Ordner
            video_path = os.path.join(word_folder, video_files[0])
            videos.append(mp.VideoFileClip(video_path))

    if videos:
        # Erstellen Sie ein Video aus den ausgewählten Videodateien
        combined_video = mp.concatenate_videoclips(videos, method="compose")

        # Speichern Sie das erstellte Video im Ausgabeordner
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, "output_video.mp4")
        combined_video.write_videofile(output_path, codec="libx264", fps=24)

        print(f"Video basierend auf dem Satz erstellt und im Ausgabeordner gespeichert: {output_path}")
    else:
        print("Für einige Wörter im Satz wurden keine Videos gefunden.")

if __name__ == "__main__":
    list_available_words()  # Liste der verfügbaren Wörter mit Videodateien anzeigen
    user_input = input("Geben Sie einen Satz ein: ")
    create_video_from_sentence(user_input)
