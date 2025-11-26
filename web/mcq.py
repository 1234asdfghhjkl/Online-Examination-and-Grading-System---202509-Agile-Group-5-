from urllib.parse import parse_qs
import html

from web.template_engine import render
from services.exam_service import get_exam_by_id
from services.question_service import (
    create_mcq_question,
    get_mcq_questions_by_exam,
    exam_exists,
    delete_mcq_question,
)


def _parse_form(body: str) -> dict:
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    return {
        "exam_id": get_field("exam_id"),
        "question_text": get_field("question_text"),
        "option_a": get_field("option_a"),
        "option_b": get_field("option_b"),
        "option_c": get_field("option_c"),
        "option_d": get_field("option_d"),
        "correct_option": get_field("correct_option"),
        "marks": get_field("marks"),
    }


def _build_questions_preview_html(exam_id: str) -> str:
    questions = get_mcq_questions_by_exam(exam_id)
    if not questions:
        return """
        <p class="text-muted small mb-0">
            No MCQ questions added yet for this exam.
        </p>
        """

    pieces = []
    for idx, q in enumerate(questions, start=1):
        opts = q.get("options", {})
        correct = q.get("correct_option", "")
        marks = q.get("marks", 0)
        qid = q.get("id", "")

        question_html = f"""
        <div class="mb-3 p-3 border rounded-3 bg-light">
            <div class="mb-2 fw-semibold">Q{idx}. {html.escape(q.get("question_text", ""))}</div>
            <div class="ms-1">
                <div class="form-check">
                    <input class="form-check-input" type="radio" disabled>
                    <label class="form-check-label">A. {html.escape(opts.get("A", ""))}</label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="radio" disabled>
                    <label class="form-check-label">B. {html.escape(opts.get("B", ""))}</label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="radio" disabled>
                    <label class="form-check-label">C. {html.escape(opts.get("C", ""))}</label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="radio" disabled>
                    <label class="form-check-label">D. {html.escape(opts.get("D", ""))}</label>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <div class="small text-muted">
                        <span class="me-3"><strong>Correct answer:</strong> {html.escape(correct)}</span>
                        <span><strong>Marks:</strong> {marks}</span>
                    </div>
                    <form action="/mcq-delete?exam_id={html.escape(exam_id)}" method="POST">
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


def get_mcq_builder(exam_id: str):
    if not exam_id:
        errors_html = """
        <div class="alert alert-danger mb-3">
            Missing exam ID. Please go back to the exam page.
        </div>
        """
        html_str = render(
            "mcq_builder.html",
            {
                "exam_id": "",
                "question_text": "",
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "correct_option": "",
                "marks": "",
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
            "mcq_builder.html",
            {
                "exam_id": exam_id,
                "question_text": "",
                "option_a": "",
                "option_b": "",
                "option_c": "",
                "option_d": "",
                "correct_option": "",
                "marks": "",
                "errors_html": errors_html,
                "success_html": "",
                "questions_preview_html": "",
            },
        )
        return html_str, 404

    preview_html = _build_questions_preview_html(exam_id)

    html_str = render(
        "mcq_builder.html",
        {
            "exam_id": exam_id,
            "question_text": "",
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "correct_option": "",
            "marks": "",
            "errors_html": "",
            "success_html": "",
            "questions_preview_html": preview_html,
        },
    )
    return html_str, 200


def post_mcq_builder(exam_id: str, body: str):
    form = _parse_form(body)
    if exam_id:
        form["exam_id"] = exam_id

    errors = []

    if not form["exam_id"]:
        errors.append("Exam ID is required.")
    if not form["question_text"].strip():
        errors.append("Question text is required.")
    if not form["option_a"].strip():
        errors.append("Option A is required.")
    if not form["option_b"].strip():
        errors.append("Option B is required.")
    if not form["option_c"].strip():
        errors.append("Option C is required.")
    if not form["option_d"].strip():
        errors.append("Option D is required.")
    if form["correct_option"] not in ("A", "B", "C", "D"):
        errors.append("Correct answer must be one of A, B, C, or D.")
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
            <strong>Unable to save MCQ:</strong>
            <ul class="mb-0">{error_items}</ul>
        </div>
        """
        preview_html = (
            _build_questions_preview_html(form["exam_id"]) if form["exam_id"] else ""
        )
        ctx = {
            "exam_id": form["exam_id"],
            "question_text": form["question_text"],
            "option_a": form["option_a"],
            "option_b": form["option_b"],
            "option_c": form["option_c"],
            "option_d": form["option_d"],
            "correct_option": form["correct_option"],
            "marks": form["marks"],
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("mcq_builder.html", ctx)
        return html_str, 400

    # Valid → save to DB
    options = {
        "A": form["option_a"],
        "B": form["option_b"],
        "C": form["option_c"],
        "D": form["option_d"],
    }

    try:
        create_mcq_question(
            exam_id=form["exam_id"],
            question_text=form["question_text"],
            options=options,
            correct_option=form["correct_option"],
            marks=int(form["marks"]),
        )
    except ValueError as exc:
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            Failed to save MCQ: {html.escape(str(exc))}
        </div>
        """
        preview_html = ""
        ctx = {
            "exam_id": form["exam_id"],
            "question_text": form["question_text"],
            "option_a": form["option_a"],
            "option_b": form["option_b"],
            "option_c": form["option_c"],
            "option_d": form["option_d"],
            "correct_option": form["correct_option"],
            "marks": form["marks"],
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("mcq_builder.html", ctx)
        return html_str, 400

    # Success → clear form, rebuild preview
    preview_html = _build_questions_preview_html(form["exam_id"])
    success_html = """
    <div class="alert alert-success mb-3">
        ✅ MCQ question saved successfully.
    </div>
    """

    ctx = {
        "exam_id": form["exam_id"],
        "question_text": "",
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_option": "",
        "marks": "",
        "errors_html": "",
        "success_html": success_html,
        "questions_preview_html": preview_html,
    }
    html_str = render("mcq_builder.html", ctx)
    return html_str, 200


def post_delete_mcq(exam_id: str, body: str):
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
        delete_mcq_question(question_id)
        success_html = """
        <div class="alert alert-success mb-3">
            🗑️ MCQ question deleted successfully.
        </div>
        """

    preview_html = _build_questions_preview_html(exam_id) if exam_id else ""

    ctx = {
        "exam_id": exam_id,
        "question_text": "",
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_option": "",
        "marks": "",
        "errors_html": errors_html,
        "success_html": success_html,
        "questions_preview_html": preview_html,
    }
    html_str = render("mcq_builder.html", ctx)
    return html_str, 200


# At least 1 question must be added before proceeding


def post_mcq_done(exam_id: str, body: str):
    if not exam_id or not exam_exists(exam_id):
        errors_html = """
        <div class="alert alert-danger mb-3">
            Exam not found. Please go back to the review page and try again.
        </div>
        """
        preview_html = ""
        ctx = {
            "exam_id": exam_id or "",
            "question_text": "",
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "correct_option": "",
            "marks": "",
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("mcq_builder.html", ctx)
        return html_str, 400

    questions = get_mcq_questions_by_exam(exam_id)

    if not questions:
        # No questions added
        errors_html = """
        <div class="alert alert-danger mb-3">
            Please add at least <strong>ONE MCQ question</strong> before completing this step.
        </div>
        """
        preview_html = _build_questions_preview_html(exam_id)
        ctx = {
            "exam_id": exam_id,
            "question_text": "",
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "correct_option": "",
            "marks": "",
            "errors_html": errors_html,
            "success_html": "",
            "questions_preview_html": preview_html,
        }
        html_str = render("mcq_builder.html", ctx)
        return html_str, 200

    # At least one question exists → decide where to go based on exam status
    exam = get_exam_by_id(exam_id)
    status = (exam or {}).get("status", "draft")

    if status == "published":
        redirect_url = f"/exam-publish?exam_id={html.escape(exam_id)}"
    else:
        redirect_url = f"/exam-review?exam_id={html.escape(exam_id)}"

    # refresh/redirect
    html_str = f"""
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url={redirect_url}">
      </head>
      <body></body>
    </html>
    """
    return html_str, 200
