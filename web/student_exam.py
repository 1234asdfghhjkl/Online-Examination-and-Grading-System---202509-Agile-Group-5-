"""
Student Exam Handler
Handles student exam access, timing, and submission
"""

import json
import html
from urllib.parse import parse_qs
from datetime import datetime

from web.template_engine import render
from services.exam_service import get_exam_by_id, get_all_published_exams
from services.question_service import (
    get_mcq_questions_by_exam,
    get_short_answer_questions_by_exam,
)
from services.exam_timing import (
    check_exam_access,
    check_student_submission_status,
    auto_submit_exam,
    get_server_time,
)
from core.firebase_db import db


def _build_questions_html(exam_id: str) -> str:
    """Build HTML for all exam questions"""
    mcq_questions = get_mcq_questions_by_exam(exam_id)
    sa_questions = get_short_answer_questions_by_exam(exam_id)

    html_parts = []

    # MCQ Questions
    if mcq_questions:
        html_parts.append(
            '<h4 class="mb-4" style="color: #667eea; font-weight: 700;">📝 Multiple Choice Questions</h4>'
        )

        for idx, q in enumerate(mcq_questions, start=1):
            opts = q.get("options", {})
            marks = q.get("marks", 0)
            q_no = q.get("question_no", idx)

            question_html = f"""
            <div class="question-card">
                <div class="question-header">
                    <span>Question {q_no}.</span>
                    {html.escape(q.get("question_text", ""))}
                    <span class="marks-badge">{marks} marks</span>
                </div>
                <div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" 
                               name="mcq_{q_no}" value="A" id="q{q_no}_a">
                        <label class="form-check-label" for="q{q_no}_a">
                            <strong>A.</strong> {html.escape(opts.get("A", ""))}
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" 
                               name="mcq_{q_no}" value="B" id="q{q_no}_b">
                        <label class="form-check-label" for="q{q_no}_b">
                            <strong>B.</strong> {html.escape(opts.get("B", ""))}
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" 
                               name="mcq_{q_no}" value="C" id="q{q_no}_c">
                        <label class="form-check-label" for="q{q_no}_c">
                            <strong>C.</strong> {html.escape(opts.get("C", ""))}
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" 
                               name="mcq_{q_no}" value="D" id="q{q_no}_d">
                        <label class="form-check-label" for="q{q_no}_d">
                            <strong>D.</strong> {html.escape(opts.get("D", ""))}
                        </label>
                    </div>
                </div>
            </div>
            """
            html_parts.append(question_html)

    # Short Answer Questions
    if sa_questions:
        html_parts.append(
            '<h4 class="mb-4 mt-5" style="color: #667eea; font-weight: 700;">✏️ Short Answer Questions</h4>'
        )

        for idx, q in enumerate(sa_questions, start=1):
            marks = q.get("marks", 0)
            q_no = q.get("question_no", idx)

            question_html = f"""
            <div class="question-card">
                <div class="question-header">
                    <span>Question {q_no}.</span>
                    {html.escape(q.get("question_text", ""))}
                    <span class="marks-badge">{marks} marks</span>
                </div>
                <div>
                    <textarea class="form-control" name="sa_{q_no}" rows="5"
                              placeholder="Type your answer here..."></textarea>
                </div>
            </div>
            """
            html_parts.append(question_html)

    if not html_parts:
        return '<p class="text-muted text-center">No questions available for this exam.</p>'

    return "\n".join(html_parts)


def get_student_dashboard(student_id: str):
    """
    Renders the student dashboard with a list of available exams
    """
    published_exams = get_all_published_exams()

    # If no student ID is provided, default to a test one
    current_student_id = student_id if student_id else "test_student_01"

    exam_list_html = ""
    if not published_exams:
        exam_list_html = """
        <div class="alert alert-info">
            No exams have been published yet.
        </div>
        """
    else:
        for exam in published_exams:
            e_id = exam.get("exam_id")
            title = html.escape(exam.get("title", "Untitled"))
            duration = exam.get("duration", 0)
            date = exam.get("exam_date", "N/A")
            time = exam.get("exam_time", "N/A")

            exam_list_html += f"""
            <div class="col-md-6 mb-4">
                <div class="card h-100 shadow-sm border-0">
                    <div class="card-body">
                        <h5 class="card-title fw-bold text-primary">{title}</h5>
                        <div class="text-muted small mb-3">
                            <div>📅 Date: {date} at {time}</div>
                            <div>⏱️ Duration: {duration} mins</div>
                        </div>
                        <a href="/student-exam?exam_id={e_id}&student_id={current_student_id}" 
                           class="btn btn-outline-primary w-100">
                           Take Exam
                        </a>
                    </div>
                </div>
            </div>
            """

    html_str = render(
        "student_dashboard.html",
        {"student_id": current_student_id, "exam_list_html": exam_list_html},
    )
    return html_str, 200


def get_student_exam(exam_id: str, student_id: str):
    """
    GET handler for student exam page
    Shows exam based on timing and access rules
    """
    if not exam_id or not student_id:
        error_html = render(
            "error.html",
            {
                "message": "Missing exam ID or student ID",
                "back_url": "/student-dashboard",
            },
        )
        return error_html, 400

    # Get exam details
    exam = get_exam_by_id(exam_id)
    if not exam:
        error_html = render(
            "error.html",
            {"message": f"Exam {exam_id} not found", "back_url": "/student-dashboard"},
        )
        return error_html, 404

    # Check access
    access_info = check_exam_access(exam_id)
    submission_info = check_student_submission_status(exam_id, student_id)

    # Determine status
    if submission_info["has_submitted"]:
        exam_status = "submitted"
        submission_time = submission_info["submission_time"]
        if isinstance(submission_time, datetime):
            submission_time = submission_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        exam_status = access_info["status"]
        submission_time = ""

    # Calculate server time offset for client
    server_time = get_server_time()

    # Prepare context
    context = {
        "exam_id": exam_id,
        "student_id": student_id,
        "student_name": "Test Student",
        "exam_title": exam.get("title", ""),
        "exam_description": exam.get("description", ""),
        "instructions": exam.get("instructions", ""),
        "duration": exam.get("duration", 0),
        "exam_status": exam_status,
        "server_time": server_time.strftime("%Y-%m-%d %H:%M:%S"),
        "server_time_offset": "0",
        "submission_time": submission_time,
        "questions_html": "",
    }

    # Add timing info if available
    if "exam_start" in access_info:
        context["exam_start_time"] = access_info["exam_start"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        context["exam_start_iso"] = access_info["exam_start"].isoformat()
    else:
        context["exam_start_time"] = "N/A"
        context["exam_start_iso"] = ""

    if "exam_end" in access_info:
        context["exam_end_time"] = access_info["exam_end"].strftime("%Y-%m-%d %H:%M:%S")
        context["exam_end_iso"] = access_info["exam_end"].isoformat()
    else:
        context["exam_end_time"] = "N/A"
        context["exam_end_iso"] = ""

    # Load questions if exam is active
    if exam_status == "active":
        context["questions_html"] = _build_questions_html(exam_id)

    html_str = render("student_exam.html", context)
    return html_str, 200


def post_submit_student_exam(body: str):
    """
    POST handler for student exam submission
    """
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    exam_id = get_field("exam_id")
    student_id = get_field("student_id")
    answers_json = get_field("answers")

    # Validate
    if not exam_id or not student_id:
        return "<h1>Error: Missing required fields</h1>", 400

    # Check if already submitted
    submission_info = check_student_submission_status(exam_id, student_id)

    if submission_info["has_submitted"]:
        error_html = render(
            "error.html",
            {
                "message": "You have already submitted this exam",
                "back_url": f"/student-exam?exam_id={exam_id}&student_id={student_id}",
            },
        )
        return error_html, 400

    # Parse answers
    try:
        answers = json.loads(answers_json) if answers_json else {}
    except json.JSONDecodeError:
        answers = {}

    # Save submission
    submission_data = {
        "exam_id": exam_id,
        "student_id": student_id,
        "answers": answers,
        "submitted_at": get_server_time(),
        "auto_submitted": False,
        "status": "completed",
    }

    doc_ref = db.collection("submissions").document()
    doc_ref.set(submission_data)

    # Redirect back to exam page (will show submitted status)
    success_html = f"""
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url=/student-exam?exam_id={exam_id}&student_id={student_id}">
      </head>
      <body>Submitting...</body>
    </html>
    """
    return success_html, 200


def api_check_exam_status(exam_id: str, student_id: str):
    """
    API endpoint to check exam status (returns JSON)
    """
    access_info = check_exam_access(exam_id)
    submission_info = check_student_submission_status(exam_id, student_id)

    if submission_info["has_submitted"]:
        status = "submitted"
    else:
        status = access_info["status"]

    response = {
        "status": status,
        "can_access": access_info.get("can_access", False),
        "message": access_info.get("message", ""),
        "server_time": get_server_time().isoformat(),
        "time_remaining": access_info.get("time_remaining"),
    }

    return json.dumps(response), 200


def api_auto_submit_exam(body: str):
    """
    API endpoint for auto-submitting exam when time expires
    """
    try:
        data = json.loads(body)
        exam_id = data.get("exam_id")
        student_id = data.get("student_id")
        answers = data.get("answers", {})

        if not exam_id or not student_id:
            return json.dumps({"error": "Missing required fields"}), 400

        # Check if already submitted
        submission_info = check_student_submission_status(exam_id, student_id)
        if submission_info["has_submitted"]:
            return json.dumps({"error": "Already submitted"}), 400

        # Auto-submit
        submission_id = auto_submit_exam(exam_id, student_id, answers)

        return json.dumps({"success": True, "submission_id": submission_id}), 200

    except Exception as e:
        return json.dumps({"error": str(e)}), 500


def api_save_draft(body: str):
    """
    API endpoint for saving draft answers
    """
    try:
        data = json.loads(body)
        exam_id = data.get("exam_id")
        student_id = data.get("student_id")
        answers = data.get("answers", {})

        if not exam_id or not student_id:
            return json.dumps({"error": "Missing required fields"}), 400

        # Save draft
        draft_data = {
            "exam_id": exam_id,
            "student_id": student_id,
            "answers": answers,
            "saved_at": get_server_time(),
            "is_draft": True,
        }

        # Use student_id + exam_id as document ID to overwrite
        doc_id = f"{student_id}_{exam_id}_draft"
        db.collection("drafts").document(doc_id).set(draft_data)

        return json.dumps({"success": True}), 200

    except Exception as e:
        return json.dumps({"error": str(e)}), 500
