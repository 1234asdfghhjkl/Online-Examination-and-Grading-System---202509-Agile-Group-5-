import os
import html as _html
import re

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

    # DEBUG
    if "start_time" in context:
        print(f"DEBUG template_engine: Rendering {template_name}")
        print(f"  Context has start_time: '{context.get('start_time')}'")
        print(f"  Context has end_time: '{context.get('end_time')}'")

    # ==========================================
    # NEW: Handle {% if variable %} ... {% else %} ... {% endif %} blocks
    # ==========================================
    def process_conditionals(html: str, ctx: dict) -> str:
        # Pattern: {% if variable %} content1 {% else %} content2 {% endif %}
        pattern = r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}"

        def replacer(match):
            var_name = match.group(1)
            true_content = match.group(2)
            false_content = match.group(3)

            # Check if variable exists and is truthy
            var_value = ctx.get(var_name, "")
            if var_value and var_value != "":
                return true_content
            else:
                return false_content

        html = re.sub(pattern, replacer, html, flags=re.DOTALL)

        # Pattern: {% if variable %} content {% endif %} (no else)
        pattern_no_else = r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}"

        def replacer_no_else(match):
            var_name = match.group(1)
            content = match.group(2)

            var_value = ctx.get(var_name, "")
            if var_value and var_value != "":
                return content
            else:
                return ""

        html = re.sub(pattern_no_else, replacer_no_else, html, flags=re.DOTALL)

        return html

    # Process conditionals FIRST
    content_html = process_conditionals(content_html, context)

    # ==========================================
    # Replace {{variable}} and {{variable|safe}}
    # ==========================================
    for key, value in context.items():
        # Handle {{variable|safe}} - no escaping
        placeholder_safe = "{{" + key + "|safe}}"
        content_html = content_html.replace(placeholder_safe, str(value))

        # Handle {{variable}} - with escaping
        placeholder = "{{" + key + "}}"
        if key.endswith("_html") or key.endswith("_json"):
            # Don't escape HTML or JSON content
            replacement = str(value)
        else:
            replacement = _html.escape(str(value))
        content_html = content_html.replace(placeholder, replacement)

        # DEBUG for time fields
        if key in ["start_time", "end_time"]:
            print(f"  Replaced {placeholder} with '{replacement}'")

    # Clean up any leftover placeholders
    for leftover in ["{{errors_html}}", "{{success_html}}"]:
        content_html = content_html.replace(leftover, "")

    return base_html.replace("{{content}}", content_html)
