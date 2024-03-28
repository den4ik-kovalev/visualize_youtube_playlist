import shutil
from pathlib import Path
from time import strftime, gmtime

from dotenv import load_dotenv
# Подгружаем IMAGEIO_FFMPEG_EXE (обязательно перед moviepy)
from library.utils import download_youtube_video, mp4_to_mp3

load_dotenv()

import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, CompositeAudioClip, concatenate_videoclips
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from pydub import AudioSegment

import dirs
from library.files import XLSXFile, Folder
from library.process import run_as_process


def get_frame(
        styles: dict,
        bg_image: Image,
        main_rect: tuple,
        current_sec: int,
        duration: int
) -> Image:
    """ Получить один кадр для конкретной секунды """

    frame = bg_image.copy()
    draw = ImageDraw.Draw(frame)

    # =============== #
    # Полоска времени #
    # =============== #

    mrw = styles["v1"]["main_rect"]["width"]
    tw = styles["v1"]["timebar"]["width"]
    th = styles["v1"]["timebar"]["height"]
    tmb = styles["v1"]["timebar"]["margin_bottom"]

    rect_timebar = (
        main_rect[0] + (mrw - tw) // 2,
        main_rect[3] - tmb - th,
        main_rect[0] + (mrw - tw) // 2 + tw,
        main_rect[3] - tmb
    )

    # Заполненная часть

    color = styles["v1"]["timebar"]["color_filled"]
    border_color = styles["v1"]["timebar"]["border_color"]
    border_width = styles["v1"]["timebar"]["border_width"]

    filled_width = int(tw * current_sec / duration)
    rect_filled = (
        rect_timebar[0],
        rect_timebar[1],
        rect_timebar[0] + filled_width,
        rect_timebar[3]
    )
    draw.rectangle(rect_filled, fill=color, outline=border_color, width=border_width)

    # Незаполненная часть

    color = styles["v1"]["timebar"]["color_empty"]
    border_color = styles["v1"]["timebar"]["border_color"]
    border_width = styles["v1"]["timebar"]["border_width"]

    rect_unfilled = (
        rect_timebar[0] + filled_width,
        rect_timebar[1],
        rect_timebar[2],
        rect_timebar[3]
    )
    draw.rectangle(rect_unfilled, fill=color, outline=border_color, width=border_width)

    # ======== #
    # Кружочек #
    # ======== #

    cs = styles["v1"]["timebar"]["circle_size"]
    color = styles["v1"]["timebar"]["color_filled"]
    border_color = styles["v1"]["timebar"]["border_color"]
    border_width = styles["v1"]["timebar"]["border_width"]

    rect_circle = (
        rect_unfilled[0] - (cs // 2),
        rect_unfilled[1] - (cs // 2) + (th // 2),
        rect_unfilled[0] + (cs // 2),
        rect_unfilled[1] + (cs // 2) + (th // 2),
    )
    draw.ellipse(rect_circle, fill=color, outline=border_color, width=border_width)

    # ===== #
    # Время #
    # ===== #

    font_name = styles["v1"]["time"]["font_name"]
    font_size = styles["v1"]["time"]["font_size"]
    shift_x = styles["v1"]["time"]["shift_x"]
    shift_y = styles["v1"]["time"]["shift_y"]
    color = styles["v1"]["time"]["color"]
    stroke_color = styles["v1"]["time"]["stroke_color"]
    stroke_width = styles["v1"]["time"]["stroke_width"]

    font_path = str(dirs.fonts / font_name)
    font = ImageFont.truetype(font_path, font_size)

    # Слева
    text = strftime("%M:%S", gmtime(current_sec))
    text_width = draw.textlength(text, font=font)
    x = rect_timebar[0] - text_width - shift_x
    y = rect_timebar[1] - shift_y
    draw.text((x, y), text, font=font, fill=color, stroke_fill=stroke_color, stroke_width=stroke_width)

    # Справа
    text = strftime("%M:%S", gmtime(duration))
    x = rect_timebar[2] + shift_x
    y = rect_timebar[1] - shift_y
    draw.text((x, y), text, font=font, fill=color, stroke_fill=stroke_color, stroke_width=stroke_width)

    return frame


def visualize_song(
        styles: dict,
        url: str,
        title: str,
        bg_file: Path,
        crop_start: int = 0,
        crop_end: int = 0,
        save_dir: Path = Path.cwd(),
        silent: bool = False,
        example_frame: bool = False
) -> dict[str, Path]:
    """ Получить mp4 для одного трека или пример кадра """

    # ========================================= #
    # Фон, который не меняется от кадра к кадру #
    # ========================================= #

    w = styles["width"]
    h = styles["height"]
    blur_radius = styles["v1"]["blur_radius"]

    bg_image = Image.open(bg_file)
    bg_blur = Image.open(bg_file).filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Рамка

    bm = styles["v1"]["main_border"]["margin"]
    bw = styles["v1"]["main_border"]["width"]

    rect_left = (bm, bm, bm + bw, h - bm)
    rect_upper = (bm, bm, w - bm, bm + bw)
    rect_right = (w - bm - bw, bm, w - bm, h - bm)
    rect_lower = (bm, h - bm - bw, w - bm, h - bm)

    bg_image.paste(bg_blur.crop(rect_left), rect_left)
    bg_image.paste(bg_blur.crop(rect_upper), rect_upper)
    bg_image.paste(bg_blur.crop(rect_right), rect_right)
    bg_image.paste(bg_blur.crop(rect_lower), rect_lower)

    # Прямоугольник

    rect_w = styles["v1"]["main_rect"]["width"]
    rect_h = styles["v1"]["main_rect"]["height"]
    rect_mb = styles["v1"]["main_rect"]["margin_bottom"]
    rect_ml = (w - rect_w) // 2

    main_rect = (rect_ml, h - rect_mb - rect_h, rect_ml + rect_w, h - rect_mb)
    bg_image.paste(bg_blur.crop(main_rect), main_rect)

    # Заголовок

    font_name = styles["v1"]["title"]["font_name"]
    font_size = styles["v1"]["title"]["font_size"]
    color = styles["v1"]["title"]["color"]
    stroke_color = styles["v1"]["title"]["stroke_color"]
    stroke_width = styles["v1"]["title"]["stroke_width"]

    draw = ImageDraw.Draw(bg_image)
    font_path = str(dirs.fonts / font_name)
    font = ImageFont.truetype(font_path, font_size)
    text_width = draw.textlength(title, font=font)
    x = main_rect[0] + ((rect_w - text_width) // 2)
    y = main_rect[1] + 10
    draw.text((x, y), title, font=font, fill=color, stroke_fill=stroke_color, stroke_width=stroke_width)

    # ========================================= #
    # Отдать пример кадра, если нужен только он #
    # ========================================= #

    if example_frame:
        frame = get_frame(styles, bg_image, main_rect, current_sec=13, duration=124)
        save_path = save_dir / "frame.jpg"
        frame.save(str(save_path), format="JPEG", subsampling=0, quality=100)
        return {"jpg": save_path}

    # =========== #
    # Скачать mp3 #
    # =========== #

    song_id = url.replace("https://youtube.com/watch?v=", "")

    # Ищем в ранее скачанных
    mp3s = Folder(dirs.cache).find_by_name(f"{song_id}.mp3")
    if mp3s:
        mp3_path = mp3s[0]
    else:
        # Скачиваем видео, делаем аудио
        mp4 = download_youtube_video(url, save_dir=dirs.cache, filename=f"{song_id}.mp4")
        mp3_path = mp4_to_mp3(mp4, remove_src=True)

    # =========== #
    # Сделать mp4 #
    # =========== #

    # Ищем в ранее сделанных
    mp4s = Folder(dirs.cache).find_by_name(f"{song_id}.mp4")
    if mp4s:
        mp4_path = mp4s[0]
    else:
        # Делаем кадр для каждой секунды

        audio_clip = AudioFileClip(str(mp3_path))
        duration = int(audio_clip.duration) - crop_end - crop_start

        frames = [get_frame(styles, bg_image, main_rect, sec, duration) for sec in range(duration)]
        frames.append(get_frame(styles, bg_image, main_rect, duration, duration))
        frames.append(get_frame(styles, bg_image, main_rect, duration, duration))

        for i in range(len(frames)):
            frames[i] = ImageClip(np.array(frames[i])).set_duration(1)

        video_clip = concatenate_videoclips(frames, method="compose")
        if not silent:
            audio_clip = AudioFileClip(str(mp3_path))
            video_clip.audio = CompositeAudioClip([audio_clip])

        mp4_path = dirs.cache / f"{song_id}.mp4"
        video_clip.write_videofile(str(mp4_path), threads=8, fps=1)

    # ================================== #
    # Сохранить mp3 и mp4 куда требуется #
    # ================================== #

    mp3_save_path = save_dir / f"{song_id}.mp3"
    if mp3_save_path != mp3_path:
        shutil.copy(mp3_path, mp3_save_path)

    mp4_save_path = save_dir / f"{song_id}.mp4"
    if mp4_save_path != mp4_path:
        shutil.copy(mp4_path, mp4_save_path)

    return {"mp3": mp3_save_path, "mp4": mp4_save_path}


def visualize_playlist(
        styles: dict,
        xlsx_file: Path,
        bg_file: Path,
        save_dir: Path = Path.cwd(),
        example_frame: bool = False
) -> dict[str, Path]:
    """ Получить mp4 для всего плейлиста """

    playlist = XLSXFile(xlsx_file).read()
    playlist = [{k.lower(): v for k, v in song.items()} for song in playlist]
    processed = []

    # Отдать пример кадра, если нужен только он

    if example_frame:
        song = playlist[0]
        url = song["url"]
        title = song["title"]
        crop_start = song.get("crop_start") or 0
        crop_end = song.get("crop_end") or 0
        song_files = visualize_song(
            styles=styles,
            url=url,
            title=title,
            bg_file=bg_file,
            crop_start=crop_start,
            crop_end=crop_end,
            save_dir=save_dir,
            example_frame=True
        )
        jpg = song_files["jpg"]
        return {"jpg": jpg}

    # Получить mp3 и mp4 для каждого трека

    for song in playlist:

        url = song["url"]
        title = song["title"]
        crop_start = song.get("crop_start") or 0
        crop_end = song.get("crop_end") or 0

        song_files = run_as_process(
            visualize_song,
            styles=styles,
            url=url,
            title=title,
            bg_file=bg_file,
            crop_start=crop_start,
            crop_end=crop_end,
            save_dir=dirs.cache,
            silent=True
        )

        mp4 = song_files["mp4"]
        mp3 = song_files["mp3"]

        processed.append((mp4, mp3, url, title, crop_start, crop_end))

    # Объединить mp3 и mp4 в один файл

    mp4s = [data[0] for data in processed]
    clips = [VideoFileClip(str(mp4)) for mp4 in mp4s]
    video_clip = concatenate_videoclips(clips, method="compose")

    audio = None
    timecodes = []
    start_seconds = 0

    for _, mp3, url, title, crop_start, crop_end in processed:

        segment = AudioSegment.from_mp3(mp3)
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

    audio_clip = AudioFileClip(str(mp3_playlist))
    video_clip.audio = CompositeAudioClip([audio_clip])
    mp4_playlist = save_dir / "playlist.mp4"
    video_clip.write_videofile(str(mp4_playlist), threads=8, fps=1)

    txt_timecodes = save_dir / "timecodes.txt"
    with open(txt_timecodes, "w", encoding="utf-8") as file:
        file.writelines(timecodes)

    return {"mp4": mp4_playlist, "txt": txt_timecodes}
