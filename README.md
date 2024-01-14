# 🎬 Word-Based Video Processing

## 📝 Description
This project comprises two main scripts: `cut_youtube_to_word_video.py` and `create_video.py`. `cut_youtube_to_word_video.py` is used to download YouTube videos, convert them into audio, transcribe speech to text, and then slice the videos based on individual spoken words. `create_video.py` allows creating a continuous video from individual word videos based on a given sentence.

## 🚀 How it Works

### 📹 cut_youtube_to_word_video.py
- Downloads videos from YouTube.
- Converts videos to audio format.
- Utilizes Google Cloud Speech-to-Text API for transcribing audio recordings.
- Slices the video into segments corresponding to individual words.
- Stores information about the videos in an SQLite database.

### 🎞️ create_video.py
- Creates a video from a given sentence by combining corresponding word videos.
- Displays a list of available words with video files.
- Allows the user to input a sentence to create a video from.

## 🔒 License
This project is currently not available under an open-source license. All rights reserved. The use, reproduction, or distribution of the code without express permission of the author is prohibited.

## 🤖 Developer Note
Portions of this project were developed with assistance from OpenAI's ChatGPT, particularly in scripting and troubleshooting.

## 📦 Requirements
- Python 3
- PyTube
- MoviePy
- Google Cloud Speech-to-Text API
- SQLite3
- OpenCV
- Tkinter

## 💻 Installation and Execution
(Here, include the steps for installation and how to run your scripts.)

---

⚠️ **Disclaimer**: This README is for illustrative purposes. Please adjust the content to fit your actual project's description and requirements.
