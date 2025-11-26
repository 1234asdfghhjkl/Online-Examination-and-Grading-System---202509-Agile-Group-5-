from urllib.parse import parse_qs
import html

from web.template_engine import render
from services.question_service import (
    exam_exists,
    create_short_answer_question,
    get_short_answer_questions_by_exam,
    delete_short_answer_question,
)
from services.exam_service import get_exam_by_id


def _parse_form(body: str) -> dict:
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    return {
        "exam_id": get_field("exam_id"),
        "question_text": get_field("question_text"),
        "sample_answer": get_field("sample_answer"),
        "marks": get_field("marks"),
    }


def _build_questions_preview_html(exam_id: str) -> str:
    questions = get_short_answer_questions_by_exam(exam_id)
    if not questions:
        return """
        <p class="text-muted small mb-0">
            No short-answer questions added yet for this exam.
        </p>
        """

    pieces = []
    for idx, q in enumerate(questions, start=1):
        sa = (q.get("sample_answer") or "").strip()
        marks = q.get("marks", 0)
        qid = q.get("id", "")

        if sa:
            sample_html = f"""
                <div class="mt-2 small text-muted">
                    <strong>Sample answer :</strong>
                    <span class="ms-1">{html.escape(sa)}</span>
                </div>
            """
        else:
            sample_html = """
                <div class="mt-2 small text-muted fst-italic">
                    No sample answer provided.
                </div>
            """

        question_html = f"""
        <div class="mb-3 p-3 border rounded-3 bg-light">
            <div class="fw-semibold mb-2">Q{idx}. {html.escape(q.get("question_text", ""))}</div>
            <div class="ms-1">
                <p class="mb-1">Student Response:</p>
                <div class="border rounded-3 bg-white mb-2" style="height: 60px;"></div>

                <div class="d-flex justify-content-between align-items-center small text-muted">
                    <div>
                        <strong>Marks:</strong> {marks}
                    </div>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    {sample_html}
                    <form action="/short-delete?exam_id={html.escape(exam_id)}" method="POST" class="mb-0">
                        <input type="hidden" name="question_id" value="{html.escape(qid)}">
                        <button type="submit" class="btn btn-sm btn-outline-danger">
                            Delete question
                        </button>
                    </form>
                </div>
            </div>
        </div>
        """
        pieces.append(question_html)

    return "\n".join(pieces)


# ---------- GET handler ----------


def get_short_builder(exam_id: str):
    if not exam_id:
        errors_html = """
        <div class="alert alert-danger mb-3">
            Missing exam ID. Please go back to the exam page.
        </div>
        """
        html_str = render(
            "short_builder.html",
            {
                "exam_id": "",
                "question_text": "",
                "sample_answer": "",
                "errors_html": errors_html,
                "success_html": "",
                "questions_preview_html": "",
            },
        )
        return html_str, 400

    if not exam_exists(exam_id):
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            Exam with ID <strong>{html.escape(exam_id)}</strong> does not exist.
        </div>
        """
        html_str = render(
            "short_builder.html",
            {
                "exam_id": exam_id,
                "question_text": "",
                "sample_answer": "",
                "errors_html": errors_html,
                "success_html": "",
                "questions_preview_html": "",
            },
        )
        return html_str, 404

    preview_html = _build_questions_preview_html(exam_id)

    html_str = render(
        "short_builder.html",
        {
            "exam_id": exam_id,
            "question_text": "",
            "sample_answer": "",
            "errors_html": "",
            "success_html": "",
            "questions_preview_html": preview_html,
        },
    )
    return html_str, 200


# ---------- POST: save Short Answer ----------


def post_short_builder(exam_id: str, body: str):
    form = _parse_form(body)

    # Use exam_id from URL if present
    if exam_id:
        form["exam_id"] = exam_id

    errors = []

    if not form["exam_id"]:
        errors.append("Exam ID is required.")
    if not form["question_text"].strip():
        errors.append("Question text is required.")
    if not form["marks"].strip():
        errors.append("Marks allocation is required.")
    elif not form["marks"].isdigit() or int(form["marks"]) <= 0:
        errors.append("Marks must be a positive integer.")

    if form["exam_id"] and not exam_exists(form["exam_id"]):
        errors.append(f"Exam '{form['exam_id']}' does not exist.")

    if errors:
        error_items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Unable to save short-answer question:</strong>
            <ul class="mb-0">{error_items}</ul>
        </div>
        """
        preview_html = (
            _build_questions_preview_html(form["exam_id"]) if form["exam_id"] else ""
        )
        ctx = {
            "exam_id": form["exam_id"],
            "question_text": form["question_text"],
            "sample_answer": form["sample_answer"],
            "marks": form["marks"],
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("short_builder.html", ctx)
        return html_str, 400

    # Valid → save to DB
    try:
        create_short_answer_question(
            exam_id=form["exam_id"],
            question_text=form["question_text"],
            sample_answer=form["sample_answer"],
            marks=int(form["marks"]),
        )
    except ValueError as exc:
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            Failed to save short-answer question: {html.escape(str(exc))}
        </div>
        """
        preview_html = ""
        ctx = {
            "exam_id": form["exam_id"],
            "question_text": form["question_text"],
            "sample_answer": form["sample_answer"],
            "marks": form["marks"],
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("short_builder.html", ctx)
        return html_str, 400

    # Success: clear form, rebuild preview
    preview_html = _build_questions_preview_html(form["exam_id"])
    success_html = """
    <div class="alert alert-success mb-3">
        ✅ Short-answer question saved successfully.
    </div>
    """

    ctx = {
        "exam_id": form["exam_id"],
        "question_text": "",
        "sample_answer": "",
        "marks": "",
        "errors_html": "",
        "success_html": success_html,
        "questions_preview_html": preview_html,
    }
    html_str = render("short_builder.html", ctx)
    return html_str, 200


def post_short_delete(exam_id: str, body: str):
    data = parse_qs(body)
    question_id = data.get("question_id", [""])[0]

    errors_html = ""
    success_html = ""

    if not exam_id:
        errors_html = """
        <div class="alert alert-danger mb-3">
            Missing exam ID; cannot delete question.
        </div>
        """
    elif not question_id:
        errors_html = """
        <div class="alert alert-danger mb-3">
            Missing question ID; cannot delete question.
        </div>
        """
    else:
        delete_short_answer_question(question_id)
        success_html = """
        <div class="alert alert-success mb-3">
            🗑️ Short-answer question deleted successfully.
        </div>
        """

    preview_html = _build_questions_preview_html(exam_id) if exam_id else ""

    ctx = {
        "exam_id": exam_id,
        "question_text": "",
        "sample_answer": "",
        "marks": "",
        "errors_html": errors_html,
        "success_html": success_html,
        "questions_preview_html": preview_html,
    }
    html_str = render("short_builder.html", ctx)
    return html_str, 200


# ---------- POST: Done ----------


def post_short_done(exam_id: str, body: str):
    if not exam_id or not exam_exists(exam_id):
        errors_html = """
        <div class="alert alert-danger mb-3">
            Exam not found. Please go back to the review page and try again.
        </div>
        """
        preview_html = ""
        ctx = {
            "exam_id": exam_id,
            "question_text": "",
            "sample_answer": "",
            "marks": "",
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("short_builder.html", ctx)
        return html_str, 400

    questions = get_short_answer_questions_by_exam(exam_id)

    if not questions:
        errors_html = """
        <div class="alert alert-danger mb-3">
            Please add at least <strong>ONE short-answer question</strong> before completing this step.
        </div>
        """
        preview_html = _build_questions_preview_html(exam_id)
        ctx = {
            "exam_id": exam_id,
            "question_text": "",
            "sample_answer": "",
            "marks": "",
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("short_builder.html", ctx)
        return html_str, 200

    exam = get_exam_by_id(exam_id)
    status = (exam or {}).get("status", "draft")

    if status == "published":
        redirect_url = f"/exam-publish?exam_id={html.escape(exam_id)}"
    else:
        redirect_url = f"/exam-review?exam_id={html.escape(exam_id)}"

    html_str = f"""
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url={redirect_url}">
      </head>
      <body></body>
    </html>
    """
    return html_str, 200
