import os
from pathlib import Path
from typing import Optional

from moviepy.editor import AudioFileClip
from pytube import YouTube


def mp4_to_mp3(mp4_path: Path, remove_src=False) -> Path:
    clip = AudioFileClip(str(mp4_path))
    mp3_path = str(mp4_path).replace(".mp4", ".mp3")
    clip.write_audiofile(mp3_path)
    clip.close()
    if remove_src:
        os.remove(mp4_path)
    return Path(mp3_path)


def download_youtube_video(link: str, save_dir: Path, filename: Optional[str] = None) -> Path:
    yt = YouTube(link)
    stream = yt.streams.filter(only_audio=True).first()
    mp4_path = stream.download(output_path=str(save_dir), filename=filename)
    return Path(mp4_path)
