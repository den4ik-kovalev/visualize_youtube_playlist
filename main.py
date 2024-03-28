import multiprocessing
from pathlib import Path

from loguru import logger

from library.files import YAMLFile
from playlist_v1 import visualize_playlist as visualize_playlist_v1
from playlist_v2 import visualize_playlist as visualize_playlist_v2
from song import visualize_song


logger.add("error.log", format="{time} {level} {message}", level="ERROR")


@logger.catch
def main():

    config = YAMLFile(Path('config.yml')).read()

    xlsx_file = Path(config["xlsx_file"])
    bg_file = Path(config["bg_file"]) if config["bg_file"] else None
    img_file = Path(config["img_file"])
    mp3_file = Path(config["mp3_file"])
    styles_file = Path(config["styles_file"])
    save_dir = Path(config["save_dir"])
    mode = config["mode"]
    example_frame = config["example_frame"]

    styles = YAMLFile(styles_file).read()

    if mode == 1:
        visualize_playlist_v1(
            styles=styles,
            xlsx_file=xlsx_file,
            bg_file=bg_file,
            save_dir=save_dir,
            example_frame=example_frame
        )
    elif mode == 2:
        visualize_playlist_v2(
            styles=styles,
            xlsx_file=xlsx_file,
            img_file=img_file,
            bg_file=bg_file,
            save_dir=save_dir,
            example_frame=example_frame
        )
    elif mode == 3:
        visualize_song(
            styles=styles,
            mp3_file=mp3_file,
            img_file=img_file,
            save_dir=save_dir,
            example_frame=example_frame
        )


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
