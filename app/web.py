import pathlib
from functools import partial

from fastapi.templating import Jinja2Templates

from . import i18n


BASE = pathlib.Path(__file__).parent

tpl = Jinja2Templates(directory=BASE / "templates")


def asset(name):
    """Static file URL with its modification time, so browsers never keep a stale CSS/JS after a deploy."""
    return f"/static/{name}?v={int((BASE / 'static' / name).stat().st_mtime)}"


tpl.env.globals["asset"] = asset


def page(request, name, context=None, lang=None):
    """Render a page with the translation helpers and the browser catalog bound to one language."""
    lang = lang or i18n.lang_for(request)
    context = dict(context or {})
    context.update({
        "lang": lang,
        "t": partial(i18n.t, lang=lang),
        "n": partial(i18n.plural, lang=lang),
        "i18n_json": i18n.catalog_json(lang),
    })
    response = tpl.TemplateResponse(request, name, context)
    response.headers["Content-Language"] = lang
    return response
