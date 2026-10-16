import pathlib

from fastapi.templating import Jinja2Templates


BASE = pathlib.Path(__file__).parent

tpl = Jinja2Templates(directory=BASE / "templates")


def asset(name):
    """Static file URL with its modification time, so browsers never keep a stale CSS/JS after a deploy."""
    return f"/static/{name}?v={int((BASE / 'static' / name).stat().st_mtime)}"


def _splashes():
    """iOS launch images: one entry per committed splash-<w>x<h>-<dpr>x.png file."""
    items = []
    for path in sorted((BASE / "static" / "icons").glob("splash-*-*x.png")):
        points, scale = path.stem.removeprefix("splash-").rsplit("-", 1)
        width, height = points.split("x")
        items.append({
            "href": f"icons/{path.name}",
            "media": (
                f"screen and (device-width: {width}px) and (device-height: {height}px) "
                f"and (-webkit-device-pixel-ratio: {scale[:-1]})"
            ),
        })
    return items


tpl.env.globals["asset"] = asset
tpl.env.globals["splashes"] = _splashes()
