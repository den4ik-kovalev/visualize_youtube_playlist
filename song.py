from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps
from moviepy.editor import AudioFileClip, ImageClip, CompositeAudioClip


def visualize_song(
        styles: dict,
        mp3_file: Path,
        img_file: Path,
        save_dir: Path = Path.cwd(),
        example_frame: bool = False
) -> dict:
    """ Получить mp4 для одного трека или пример кадра """

    # ============================================================ #
    # Формирование единственного кадра (картинка на размытом фоне) #
    # ============================================================ #

    w = styles["width"]
    h = styles["height"]
    ims = styles["song"]["image"]["size"]
    imbc = styles["song"]["image"]["border_color"]
    imbw = styles["song"]["image"]["border_width"]
    blur_radius = styles["song"]["bg"]["blur_radius"]

    img_image = Image.open(img_file)
    bg_image = img_image.copy()
    img_image = img_image.resize((ims, ims))
    bgs = int(w / ims) * w
    bg_image = bg_image.resize((bgs, bgs))
    bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    bg_rect_x = (bgs - w) // 2
    bg_rect_y = (bgs - h) // 2
    bg_rect = (bg_rect_x, bg_rect_y, bg_rect_x + w, bg_rect_y + h)
    bg_image = bg_image.crop(bg_rect)
    bg_image = bg_image.resize((w, h))  # на всякий случай

    # Рамка картинки
    if imbw:
        img_image = ImageOps.expand(img_image, border=imbw, fill=imbc)
        ims += 2 * imbw

    img_rect_x = (w - ims) // 2
    img_rect_y = (h - ims) // 2
    bg_image.paste(img_image, (img_rect_x, img_rect_y))

    # ========================================= #
    # Отдать пример кадра, если нужен только он #
    # ========================================= #

    if example_frame:
        save_path = save_dir / "frame.jpg"
        bg_image.save(str(save_path), format="JPEG", subsampling=0, quality=100)
        return {"jpg": save_path}

    # =========== #
    # Сделать mp4 #
    # =========== #

    audio_clip = AudioFileClip(str(mp3_file))
    video_clip = ImageClip(np.array(bg_image)).set_duration(audio_clip.duration)
    video_clip.audio = CompositeAudioClip([audio_clip])
    mp4_song = save_dir / "song.mp4"
    video_clip.write_videofile(str(mp4_song), threads=8, fps=1)

    return {"mp4": mp4_song}
