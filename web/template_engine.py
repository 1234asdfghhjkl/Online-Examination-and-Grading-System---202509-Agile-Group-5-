import os
import html as _html

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_CURRENT_DIR)
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")


def load_template(name: str) -> str:
    path = os.path.join(TEMPLATE_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def render(template_name: str, context=None) -> str:

    if context is None:
        context = {}

    base_html = load_template("base.html")
    content_html = load_template(template_name)

    for key, value in context.items():
        placeholder = "{{" + key + "}}"
        if key.endswith("_html"):
            replacement = str(value)
        else:
            replacement = _html.escape(str(value))
        content_html = content_html.replace(placeholder, replacement)

    for leftover in ["{{errors_html}}"]:
        content_html = content_html.replace(leftover, "")

    return base_html.replace("{{content}}", content_html)
