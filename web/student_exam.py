"""
Student Exam Handler - Updated with filtering
Handles student exam access, timing, and submission with filter checks
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
from services.student_filter_service import is_student_eligible
from services.student_submission_service import get_student_submissions, get_student_performance_stats
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
    Renders the student dashboard with filtered exams
    Renders the student dashboard with a list of available exams, submissions, and performance stats.
    """

    published_exams = get_all_published_exams()

    # If no student ID is provided, default to a test one
    current_student_id = student_id if student_id else "test_student_01"

    # Build available exams HTML - FILTER BY ELIGIBILITY
    # =========================================================
    # 1. NEW: Get Performance Stats & Generate HTML
    # =========================================================
    stats = get_student_performance_stats(current_student_id)
    
    if stats['has_data']:
        stats_html = f"""
        <div class="card bg-white border-0 shadow-sm mb-4">
            <div class="card-body p-4">
                <h5 class="card-title fw-bold text-primary mb-3">📊 Performance Report</h5>
                <div class="row text-center">
                    <div class="col-md-3 col-6 mb-2">
                        <div class="p-3 rounded bg-light">
                            <div class="text-muted small">Average Score</div>
                            <div class="fs-2 fw-bold text-primary">{stats['average']}%</div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="p-3 rounded bg-light">
                            <div class="text-muted small">Exams Taken</div>
                            <div class="fs-2 fw-bold text-dark">{stats['total_exams']}</div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="p-3 rounded bg-light">
                            <div class="text-muted small">Highest</div>
                            <div class="fs-2 fw-bold text-success">{stats['highest']}%</div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="p-3 rounded bg-light">
                            <div class="text-muted small">Lowest</div>
                            <div class="fs-2 fw-bold text-danger">{stats['lowest']}%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        stats_html = "" # No stats to show yet

    # =========================================================
    # 2. Build Available Exams List HTML
    # =========================================================
    exam_list_html = ""
    eligible_exams = []
    
    for exam in published_exams:
        e_id = exam.get("exam_id")
        
        # CHECK ELIGIBILITY
        if is_student_eligible(current_student_id, e_id):
            eligible_exams.append(exam)
    
    if not eligible_exams:
        exam_list_html = """
        <div class="alert alert-info">
            <h5>📚 No Exams Available</h5>
            <p class="mb-0">There are no exams currently available for you. Check back later!</p>
        </div>
        """
    else:
        for exam in eligible_exams:
            e_id = exam.get("exam_id")
            title = html.escape(exam.get("title", "Untitled"))
            duration = exam.get("duration", 0)
            date = exam.get("exam_date", "N/A")

            # Handle both old and new time formats
            start_time = exam.get("start_time", exam.get("exam_time", "N/A"))

            exam_list_html += f"""
            <div class="col-md-6 mb-4">
                <div class="card h-100 shadow-sm border-0">
                    <div class="card-body">
                        <h5 class="card-title fw-bold text-primary">{title}</h5>
                        <div class="text-muted small mb-3">
                            <div>📅 Date: {date} at {start_time}</div>
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

    # =========================================================
    # 3. Build Submissions List HTML
    # =========================================================
    submissions = get_student_submissions(current_student_id)
    submissions_html = ""

    if not submissions:
        submissions_html = """
        <div class="alert alert-info">
            <p class="mb-0">You haven't submitted any exams yet.</p>
        </div>
        """
    else:
        for sub in submissions:
            exam_title = html.escape(sub.get("exam_title", "Unknown Exam"))
            exam_date = sub.get("exam_date", "N/A")
            submitted_at = sub.get("submitted_at")

            if isinstance(submitted_at, datetime):
                submitted_time = submitted_at.strftime("%Y-%m-%d %H:%M")
            else:
                submitted_time = "N/A"

            exam_id = sub.get("exam_id")
            results_released = sub.get("results_released", False)
            release_date = sub.get("release_date")
            release_time = sub.get("release_time", "00:00")

            if results_released:
                status_badge = '<span class="status-badge status-released">✅ Results Available</span>'
                action_button = f"""
                <a href="/student-result?exam_id={exam_id}&student_id={current_student_id}" 
                   class="btn btn-success btn-sm">
                    View Results
                </a>
                """
                score_display = f"""
                <div class="mt-2">
                    <strong>Score:</strong> {sub.get('overall_percentage', 0)}%
                </div>
                """
            else:
                status_badge = '<span class="status-badge status-pending">⏳ Results Pending</span>'
                if release_date:
                    release_display = f"{release_date} at {release_time}"
                    action_button = f"""
                    <button class="btn btn-outline-secondary btn-sm" disabled>
                        Results on {release_display}
                    </button>
                    """
                else:
                    action_button = """
                    <button class="btn btn-outline-secondary btn-sm" disabled>
                        Results Not Yet Scheduled
                    </button>
                    """
                score_display = ""

            submissions_html += f"""
            <div class="submission-card">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h6 class="mb-2">
                            <strong>{exam_title}</strong>
                            {status_badge}
                        </h6>
                        <div class="text-muted small">
                            <div>📅 Exam Date: {exam_date}</div>
                            <div>📤 Submitted: {submitted_time}</div>
                            {score_display}
                        </div>
                    </div>
                    <div class="col-md-4 text-end">
                        {action_button}
                    </div>
                </div>
            </div>
            """

    # =========================================================
    # 4. Render Template
    # =========================================================
    html_str = render(
        "student_dashboard.html",
        {
            "student_id": current_student_id,
            "exam_list_html": exam_list_html,
            "submissions_html": submissions_html,
            "stats_html": stats_html,  # <--- PASS THE STATS HTML HERE
        },
    )
    return html_str, 200


def get_student_exam(exam_id: str, student_id: str):
    """
    GET handler for student exam page
    Shows exam based on timing, access rules, AND ELIGIBILITY
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

    # CHECK ELIGIBILITY
    if not is_student_eligible(student_id, exam_id):
        error_html = render(
            "error.html",
            {
                "message": "You are not eligible to take this exam. This exam is restricted to specific student groups.",
                "back_url": f"/student-dashboard?student_id={student_id}",
            },
        )
        return error_html, 403

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
    from services.grading_service import grade_mcq_submission, save_grading_result

    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    exam_id = get_field("exam_id")
    student_id = get_field("student_id")
    answers_json = get_field("answers")

    # Validate
    if not exam_id or not student_id:
        return "<h1>Error: Missing required fields</h1>", 400

    # Check eligibility
    if not is_student_eligible(student_id, exam_id):
        error_html = render(
            "error.html",
            {
                "message": "You are not eligible to submit this exam.",
                "back_url": f"/student-dashboard?student_id={student_id}",
            },
        )
        return error_html, 403

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
    submission_id = doc_ref.id

    # AUTO-GRADE MCQ QUESTIONS
    grading_result = grade_mcq_submission(exam_id, student_id, answers)
    save_grading_result(submission_id, grading_result)

    success_html = f"""
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url=/student-dashboard?student_id={student_id}">
      </head>
      <body>Submission successful. Redirecting to dashboard...</body>
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


def get_exam_result(exam_id: str, student_id: str):
    """
    Display exam results for a student
    """
    from services.grading_service import get_student_submission

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

    # Get submission
    submission = get_student_submission(exam_id, student_id)
    if not submission:
        error_html = render(
            "error.html",
            {
                "message": "No submission found for this exam",
                "back_url": f"/student-dashboard?student_id={student_id}",
            },
        )
        return error_html, 404

    # Get grading result
    grading_result = submission.get("grading_result", {})

    if not grading_result:
        error_html = render(
            "error.html",
            {
                "message": "Results are being processed. Please check back in a moment.",
                "back_url": f"/student-dashboard?student_id={student_id}",
            },
        )
        return error_html, 404

    # Build question review HTML
    questions_review_html = ""
    for q_result in grading_result.get("question_results", []):
        is_correct = q_result.get("is_correct")
        student_answer = q_result.get("student_answer", "")
        correct_answer = q_result.get("correct_answer", "")

        if not student_answer or student_answer == "Not answered":
            status_class = "unanswered"
            status_icon = "⚠️"
        elif is_correct:
            status_class = "correct"
            status_icon = "✅"
        else:
            status_class = "incorrect"
            status_icon = "❌"

        questions_review_html += f"""
        <div class="question-item {status_class}">
            <div class="question-header">
                <span class="status-icon">{status_icon}</span>
                <div>
                    <strong>Question {q_result.get('question_no')}</strong>
                    <div class="text-muted small">
                        {q_result.get('marks_obtained')}/{q_result.get('marks')} marks
                    </div>
                </div>
            </div>
            <div>{html.escape(q_result.get('question_text', ''))}</div>
            <div class="answer-info">
                <div><strong>Your answer:</strong> {html.escape(student_answer)}</div>
                <div><strong>Correct answer:</strong> {html.escape(correct_answer)}</div>
            </div>
        </div>
        """

    # Add short answer results if available
    sa_grades = submission.get("short_answer_graded_questions", [])
    if sa_grades:
        questions_review_html += (
            '<h4 class="mb-4 mt-5" style="color: #667eea;">✏️ Short Answer Results</h4>'
        )

        for sa in sa_grades:
            q_no = sa.get("question_no")
            awarded = sa.get("awarded_marks", 0)
            max_marks = sa.get("max_marks", 0)
            feedback = sa.get("feedback", "")

            questions_review_html += f"""
            <div class="question-item">
                <div class="question-header">
                    <strong>Question {q_no}</strong>
                    <div class="text-muted small">
                        {awarded}/{max_marks} marks
                    </div>
                </div>
                {f'<div class="answer-info"><strong>Feedback:</strong> {html.escape(feedback)}</div>' if feedback else ''}
            </div>
            """

    context = {
        "exam_id": exam_id,
        "student_id": student_id,
        "exam_title": exam.get("title", ""),
        "total_marks": grading_result.get("total_marks", 0),
        "obtained_marks": grading_result.get("obtained_marks", 0),
        "percentage": grading_result.get("percentage", 0),
        "total_questions": grading_result.get("total_questions", 0),
        "correct_answers": grading_result.get("correct_answers", 0),
        "incorrect_answers": grading_result.get("incorrect_answers", 0),
        "unanswered": grading_result.get("unanswered", 0),
        "questions_review_html": questions_review_html,
    }

    html_str = render("exam_result.html", context)
    return html_str, 200

