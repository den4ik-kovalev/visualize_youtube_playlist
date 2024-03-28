from pathlib import Path


static = Path.cwd() / "static"
fonts = Path.cwd() / "fonts"
cache = Path.cwd() / "cache"

cache.mkdir(exist_ok=True)
