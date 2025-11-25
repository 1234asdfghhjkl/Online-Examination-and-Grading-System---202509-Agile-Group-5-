from urllib.parse import parse_qs
import html

from core.validation import validate_exam, validate_exam_date
from services.exam_service import create_exam
from .template_engine import render


def _parse_form(body: str) -> dict:
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    return {
        "title": get_field("title"),
        "description": get_field("description"),
        "duration": get_field("duration"),
        "exam_date": get_field("exam_date"),
        "instructions": get_field("instructions"),
    }


# ---------- GET handlers ----------


def get_create_exam():
    html_str = render(
        "create_exam.html",
        {
            "title": "",
            "description": "",
            "duration": "",
            "exam_date": "",
            "instructions": "",
            "errors_html": "",
        },
    )
    return html_str, 200


# ---------- POST handlers ----------


def post_submit_exam(body: str):
    form = _parse_form(body)

    errors = validate_exam(
        form["title"], form["description"], form["duration"], form["instructions"]
    )
    errors.extend(validate_exam_date(form["exam_date"]))

    if errors:
        error_items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Please fix the following:</strong>
            <ul class="mb-0">{error_items}</ul>
        </div>
        """
        ctx = dict(form)
        ctx["errors_html"] = errors_html
        html_str = render("create_exam.html", ctx)
        return html_str, 400

    # Valid → show draft/review page
    html_str = render("exam_review.html", form)
    return html_str, 200


def post_edit_exam(body: str):
    # Re-show the form with the same values
    form = _parse_form(body)
    ctx = dict(form)
    ctx["errors_html"] = ""
    html_str = render("create_exam.html", ctx)
    return html_str, 200


def post_publish_exam(body: str):
    form = _parse_form(body)

    errors = validate_exam(
        form["title"], form["description"], form["duration"], form["instructions"]
    )
    errors.extend(validate_exam_date(form["exam_date"]))

    if errors:
        error_items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Please fix the following:</strong>
            <ul class="mb-0">{error_items}</ul>
        </div>
        """
        ctx = dict(form)
        ctx["errors_html"] = errors_html
        html_str = render("create_exam.html", ctx)
        return html_str, 400

    # Final save to DB
    exam_id = create_exam(
        form["title"],
        form["description"],
        form["duration"],
        form["instructions"],
        form["exam_date"],
    )

    ctx = dict(form)
    ctx["exam_id"] = exam_id
    html_str = render("exam_published.html", ctx)
    return html_str, 200
