from pathlib import Path
from time import strftime, gmtime
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from moviepy.editor import AudioFileClip, ImageClip, CompositeAudioClip, concatenate_videoclips
from pydub import AudioSegment

import dirs
from library.files import XLSXFile, Folder
from library.utils import download_youtube_video, mp4_to_mp3


def get_frame(
        styles: dict,
        bg_image: Image,
        tracklist_coords: tuple,
        titles: list[str],
        current_title: str
) -> Image:
    """ Получить один кадр для конкретного трека """

    frame = bg_image.copy()
    draw = ImageDraw.Draw(frame)

    font_name = styles["v2"]["tracklist"]["font_name"]
    font_size = styles["v2"]["tracklist"]["font_size"]
    color_default = styles["v2"]["tracklist"]["color_default"]
    color_current = styles["v2"]["tracklist"]["color_current"]
    stroke_color = styles["v2"]["tracklist"]["stroke_color"]
    stroke_width = styles["v2"]["tracklist"]["stroke_width"]
    line_height = styles["v2"]["tracklist"]["line_height"]

    font_path = str(dirs.fonts / font_name)
    font = ImageFont.truetype(font_path, font_size)

    for idx, title in enumerate(titles):
        x, y = tracklist_coords
        y += idx * line_height
        color = color_current if title is current_title else color_default
        text = f"{idx + 1}. {title}"
        draw.text((x, y), text, font=font, fill=color, stroke_fill=stroke_color, stroke_width=stroke_width)

    return frame


def visualize_playlist(
        styles: dict,
        xlsx_file: Path,
        img_file: Path,
        bg_file: Optional[Path] = None,
        save_dir: Path = Path.cwd(),
        example_frame: bool = False
) -> dict[str, Path]:
    """ Получить mp4 для всего плейлиста """

    playlist = XLSXFile(xlsx_file).read()
    playlist = [{k.lower(): v for k, v in song.items()} for song in playlist]
    processed = []

    # ========================================= #
    # Фон, который не меняется от кадра к кадру #
    # ========================================= #

    w = styles["width"]
    h = styles["height"]
    bgc = styles["v2"]["bg_color"]
    ims = styles["v2"]["image"]["size"]
    imbc = styles["v2"]["image"]["border_color"]
    imbw = styles["v2"]["image"]["border_width"]
    tx = styles["v2"]["tracklist"]["x"]
    ty = styles["v2"]["tracklist"]["y"]

    if bg_file:
        bg_image = Image.open(bg_file)
    else:
        bg_image = Image.new("RGB", (w, h), bgc)

    img_image = Image.open(img_file)
    img_image = img_image.resize((ims, ims))

    # Рамка картинки
    if imbw:
        img_image = ImageOps.expand(img_image, border=imbw, fill=imbc)
        ims += 2 * imbw

    img_margin = (h - ims) // 2
    bg_image.paste(img_image, (img_margin, img_margin))

    # ========================================= #
    # Отдать пример кадра, если нужен только он #
    # ========================================= #

    if example_frame:
        titles = [song["title"] for song in playlist]
        frame = get_frame(styles, bg_image, (tx, ty), titles=titles, current_title=titles[0])
        save_path = save_dir / "frame.jpg"
        frame.save(str(save_path), format="JPEG", subsampling=0, quality=100)
        return {"jpg": save_path}

    # =========== #
    # Скачать mp3 #
    # =========== #

    for song in playlist:

        url = song["url"]
        title = song["title"]
        crop_start = song.get("crop_start") or 0
        crop_end = song.get("crop_end") or 0

        song_id = url.replace("https://youtube.com/watch?v=", "")

        # Ищем в ранее скачанных
        mp3s = Folder(dirs.cache).find_by_name(f"{song_id}.mp3")
        if mp3s:
            mp3_path = mp3s[0]
        else:
            # Скачиваем видео, делаем аудио
            mp4 = download_youtube_video(url, save_dir=dirs.cache, filename=f"{song_id}.mp4")
            mp3_path = mp4_to_mp3(mp4, remove_src=True)

        processed.append((mp3_path, url, title, crop_start, crop_end))

    # =========== #
    # Сделать mp4 #
    # =========== #

    titles = [data[2] for data in processed]

    video_clip_parts = []

    audio = None
    timecodes = []
    start_seconds = 0

    # Объединить mp3 и mp4 в один файл

    for mp3_path, url, title, crop_start, crop_end in processed:

        audio_clip = AudioFileClip(str(mp3_path))
        duration = int(audio_clip.duration) - crop_end - crop_start

        frame = get_frame(styles, bg_image, (tx, ty), titles=titles, current_title=title)
        clip = ImageClip(np.array(frame)).set_duration(duration + 2)
        video_clip_parts.append(clip)

        segment = AudioSegment.from_mp3(mp3_path)
        duration = int(segment.duration_seconds) - crop_end - crop_start
        segment = segment[(crop_start * 1000):((crop_start + duration) * 1000)]
        if audio is None:
            audio = segment
        else:
            audio = audio.append(segment, crossfade=100)
        silence = AudioSegment.from_mp3(str(dirs.static / "silence22.mp3"))
        silence = silence[:2200]
        audio = audio.append(silence, crossfade=100)

        timecode = strftime("%M:%S", gmtime(start_seconds))
        timecodes.append(f"{timecode} {title} ({url})\n")
        start_seconds += (duration + 2)

    mp3_playlist = dirs.cache / "playlist.mp3"
    audio.export(str(mp3_playlist), format="mp3")

    video_clip = concatenate_videoclips(video_clip_parts, method="compose")
    audio_clip = AudioFileClip(str(mp3_playlist))
    video_clip.audio = CompositeAudioClip([audio_clip])

    mp4_playlist = save_dir / "playlist.mp4"
    video_clip.write_videofile(str(mp4_playlist), threads=8, fps=1)

    txt_timecodes = save_dir / "timecodes.txt"
    with open(txt_timecodes, "w", encoding="utf-8") as file:
        file.writelines(timecodes)

    return {"mp4": mp4_playlist, "txt": txt_timecodes}
