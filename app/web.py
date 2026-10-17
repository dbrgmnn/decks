import pathlib

from fastapi.templating import Jinja2Templates


BASE = pathlib.Path(__file__).parent

tpl = Jinja2Templates(directory=BASE / "templates")


def asset(name):
    """Static file URL with its modification time, so browsers never keep a stale CSS/JS after a deploy."""
    return f"/static/{name}?v={int((BASE / 'static' / name).stat().st_mtime)}"


tpl.env.globals["asset"] = asset
