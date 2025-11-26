from urllib.parse import parse_qs
import html

from core.validation import validate_exam, validate_exam_date
from services.exam_service import save_exam_draft, publish_exam, get_exam_by_id
from services.question_service import has_mcq_for_exam, has_short_for_exam
from .template_engine import render


def _parse_form(body: str) -> dict:
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    return {
        "exam_id": get_field("exam_id"),
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
            "exam_id": "",
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

    # Valid : Save/update draft in DB
    exam_id = save_exam_draft(
        exam_id=form["exam_id"] or None,
        title=form["title"],
        description=form["description"],
        duration=form["duration"],
        instructions=form["instructions"],
        exam_date=form["exam_date"],
    )

    has_mcq = has_mcq_for_exam(exam_id)
    has_short = has_short_for_exam(exam_id)

    ctx = dict(form)
    ctx["exam_id"] = exam_id

    # MCQ button
    if has_mcq:
        ctx["mcq_button_label"] = "View / Edit MCQ"
        ctx["mcq_button_class"] = "btn btn-primary"
    else:
        ctx["mcq_button_label"] = "Build MCQ"
        ctx["mcq_button_class"] = "btn btn-outline-primary"

    # Short Answer button
    if has_short:
        ctx["short_button_label"] = "View / Edit Short Answers"
        ctx["short_button_class"] = "btn btn-primary"
    else:
        ctx["short_button_label"] = "Build Short Answers"
        ctx["short_button_class"] = "btn btn-outline-primary"

    html_str = render("exam_review.html", ctx)
    return html_str, 200


def post_edit_exam(body: str):
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

    if not form["exam_id"]:
        errors.append("Missing exam ID. Please save the exam again.")

    if errors:
        error_items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Unable to publish exam:</strong>
            <ul class="mb-0">{error_items}</ul>
        </div>
        """
        ctx = dict(form)
        ctx["errors_html"] = errors_html
        html_str = render("create_exam.html", ctx)
        return html_str, 400

    exam_id = save_exam_draft(
        exam_id=form["exam_id"],
        title=form["title"],
        description=form["description"],
        duration=form["duration"],
        instructions=form["instructions"],
        exam_date=form["exam_date"],
    )

    # Change status to published
    publish_exam(exam_id)

    ctx = dict(form)
    ctx["exam_id"] = exam_id
    html_str = render("exam_published.html", ctx)
    return html_str, 200


def get_exam_review(exam_id: str):
    if not exam_id:
        html_str = render(
            "exam_review.html",
            {
                "exam_id": "",
                "title": "",
                "description": "",
                "duration": "",
                "exam_date": "",
                "instructions": "",
                "mcq_button_label": "Build MCQ",
                "mcq_button_class": "btn btn-outline-primary",
                "short_button_label": "Build Short Answers",
                "short_button_class": "btn btn-outline-primary",
            },
        )
        return html_str, 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        html_str = render(
            "exam_review.html",
            {
                "exam_id": exam_id,
                "title": "Exam not found",
                "description": "",
                "duration": "",
                "exam_date": "",
                "instructions": "",
                "mcq_button_label": "Build MCQ",
                "mcq_button_class": "btn btn-outline-primary",
                "short_button_label": "Build Short Answers",
                "short_button_class": "btn btn-outline-primary",
            },
        )
        return html_str, 404

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": exam.get("duration", ""),
        "exam_date": exam.get("exam_date", ""),
        "instructions": exam.get("instructions", ""),
    }

    has_mcq = has_mcq_for_exam(ctx["exam_id"])
    has_short = has_short_for_exam(ctx["exam_id"])

    # MCQ button
    if has_mcq:
        ctx["mcq_button_label"] = "View / Edit MCQ"
        ctx["mcq_button_class"] = "btn btn-primary"
    else:
        ctx["mcq_button_label"] = "Build MCQ"
        ctx["mcq_button_class"] = "btn btn-outline-primary"

    # Short Answer button
    if has_short:
        ctx["short_button_label"] = "View / Edit Short Answers"
        ctx["short_button_class"] = "btn btn-primary"
    else:
        ctx["short_button_label"] = "Build Short Answers"
        ctx["short_button_class"] = "btn btn-outline-primary"

    html_str = render("exam_review.html", ctx)
    return html_str, 200


def get_exam_published(exam_id: str):
    if not exam_id:
        html_str = render(
            "exam_published.html",
            {
                "exam_id": "",
                "title": "",
                "description": "",
                "duration": "",
                "exam_date": "",
                "instructions": "",
            },
        )
        return html_str, 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        # Exam not found in DB
        html_str = render(
            "exam_published.html",
            {
                "exam_id": exam_id,
                "title": f"Exam {exam_id} not found",
                "description": "",
                "duration": "",
                "exam_date": "",
                "instructions": "",
            },
        )
        return html_str, 404

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": exam.get("duration", ""),
        "exam_date": exam.get("exam_date", ""),
        "instructions": exam.get("instructions", ""),
    }

    html_str = render("exam_published.html", ctx)
    return html_str, 200
