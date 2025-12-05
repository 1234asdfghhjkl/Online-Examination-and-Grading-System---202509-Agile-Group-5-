import html
from datetime import datetime
from urllib.parse import parse_qs

from core.firebase_db import db
from services.exam_service import get_exam_by_id
from services.short_answer_grading_service import (
    get_all_submissions_for_exam,
    get_submission_with_questions,
    save_short_answer_grades,
)
from .template_engine import render


def _check_grading_locked(exam: dict) -> tuple[bool, str]:
    """
    Helper to check if grading is locked based on deadline.
    Returns (is_locked, message)
    """
    deadline_date = exam.get("grading_deadline_date")
    deadline_time = exam.get("grading_deadline_time", "23:59")

    if not deadline_date:
        return False, "No deadline set"

    try:
        deadline_str = f"{deadline_date} {deadline_time}"
        deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")

        if datetime.now() > deadline_dt:
            return True, f"Grading closed on {deadline_str}"

        return False, f"Grading open until {deadline_str}"
    except ValueError:
        return False, "Invalid deadline format"


def get_grading_dashboard(exam_id: str):
    """
    Lecturer dashboard to see all students and grading status
    """
    if not exam_id:
        return "Missing Exam ID", 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        return "Exam not found", 404

    # Check Lock Status
    is_locked, lock_msg = _check_grading_locked(exam)

    submissions = get_all_submissions_for_exam(exam_id)

    submissions_html = ""
    for sub in submissions:
        student_id = sub.get("student_id", "Unknown")
        sub_id = sub.get("submission_id")

        # Status Badges
        mcq_status = (
            '<span class="badge bg-success">Auto-Graded</span>'
            if sub.get("mcq_graded")
            else '<span class="badge bg-secondary">Pending</span>'
        )

        sa_status = ""
        if sub.get("sa_graded"):
            sa_status = '<span class="badge bg-success">Graded</span>'
            action_btn = f'<a href="/grade-submission?submission_id={sub_id}" class="btn btn-sm btn-outline-secondary">Review</a>'
        else:
            sa_status = '<span class="badge bg-warning text-dark">Needs Grading</span>'
            if is_locked:
                action_btn = (
                    '<button class="btn btn-sm btn-secondary" disabled>Locked</button>'
                )
            else:
                action_btn = f'<a href="/grade-submission?submission_id={sub_id}" class="btn btn-sm btn-primary">Grade Now</a>'

        submissions_html += f"""
        <tr>
            <td>{html.escape(student_id)}</td>
            <td>{mcq_status}</td>
            <td>{sa_status}</td>
            <td>{sub.get("submitted_at", "N/A")}</td>
            <td class="text-end">{action_btn}</td>
        </tr>
        """

    lock_alert = ""
    if is_locked:
        lock_alert = f"""
        <div class="alert alert-danger d-flex align-items-center">
            <span class="fs-4 me-2">🔒</span>
            <div>
                <strong>Grading Period Ended.</strong><br>
                The deadline for this exam was {exam.get('grading_deadline_date')} {exam.get('grading_deadline_time')}. 
                You can view submissions but cannot make changes.
            </div>
        </div>
        """
    else:
        lock_alert = f"""
        <div class="alert alert-info d-flex align-items-center">
             <span class="fs-4 me-2">⏰</span>
             <div>
                <strong>Grading Deadline:</strong> {exam.get('grading_deadline_date')} at {exam.get('grading_deadline_time', '23:59')}
             </div>
        </div>
        """

    ctx = {
        "exam_title": exam.get("title"),
        "exam_id": exam_id,
        "submissions_list": submissions_html,
        "lock_alert": lock_alert,
    }

    return render("grading_dashboard.html", ctx), 200


def get_grade_submission_view(submission_id: str):
    """
    The actual grading interface for a specific student
    """
    submission = get_submission_with_questions(submission_id)
    if not submission:
        return "Submission not found", 404

    exam = get_exam_by_id(submission.get("exam_id"))
    is_locked, lock_msg = _check_grading_locked(exam)

    # Generate questions HTML
    questions_html = ""
    for q in submission.get("short_answer_questions", []):
        q_no = q.get("question_no")

        # Read-only attributes if locked
        disabled_attr = "disabled" if is_locked else ""
        readonly_cls = "bg-light" if is_locked else ""

        questions_html += f"""
        <div class="card mb-4 shadow-sm">
            <div class="card-header bg-light">
                <strong>Q{q_no}:</strong> {html.escape(q['question_text'])} 
                <span class="badge bg-secondary float-end">{q['max_marks']} Marks</span>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label text-muted">Student Answer:</label>
                    <div class="p-3 bg-light border rounded">
                        {html.escape(q['student_answer'])}
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label text-success">Sample Answer:</label>
                    <div class="small text-muted mb-1">{html.escape(q['sample_answer'])}</div>
                </div>
                
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label fw-bold">Marks Awarded</label>
                        <input type="number" name="marks_{q_no}" 
                               class="form-control {readonly_cls}" 
                               value="{q['awarded_marks']}" 
                               min="0" max="{q['max_marks']}"
                               required {disabled_attr}>
                    </div>
                    <div class="col-md-9">
                        <label class="form-label fw-bold">Feedback</label>
                        <input type="text" name="feedback_{q_no}" 
                               class="form-control {readonly_cls}" 
                               value="{q.get('feedback', '')}"
                               placeholder="Optional feedback for student..." 
                               {disabled_attr}>
                    </div>
                </div>
            </div>
        </div>
        """

    # Form actions
    if is_locked:
        actions_html = """
        <div class="alert alert-danger">
            <strong>Grading Locked.</strong> You cannot save changes.
        </div>
        <a href="/admin/grade-dashboard?exam_id={}" class="btn btn-secondary">Back</a>
        """.format(
            exam.get("exam_id")
        )
    else:
        actions_html = f"""
        <div class="d-flex justify-content-between">
            <a href="/admin/grade-dashboard?exam_id={exam.get("exam_id")}" class="btn btn-outline-secondary">Cancel</a>
            <button type="submit" class="btn btn-primary btn-lg">💾 Save Grades</button>
        </div>
        """

    ctx = {
        "student_id": submission.get("student_id"),
        "exam_title": exam.get("title"),
        "submission_id": submission_id,
        "questions_html": questions_html,
        "actions_html": actions_html,
    }

    return render("grading_view.html", ctx), 200


def post_save_grades(body: str):
    """
    Handle grade submission with STRICT LOCK CHECK
    """
    form = parse_qs(body)
    submission_id = form.get("submission_id", [""])[0]

    # 1. Fetch Data
    submission = get_submission_with_questions(submission_id)
    if not submission:
        return "Submission not found", 404

    exam = get_exam_by_id(submission.get("exam_id"))

    # 2. STRICT SECURITY CHECK: Is grading locked?
    is_locked, lock_msg = _check_grading_locked(exam)
    if is_locked:
        return (
            f"""
        <div style="padding: 20px; font-family: sans-serif; color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb;">
            <h2>⛔ Action Denied</h2>
            <p><strong>{lock_msg}</strong></p>
            <p>You cannot save grades after the deadline.</p>
            <a href="/admin/grade-dashboard?exam_id={submission.get('exam_id')}">Return to Dashboard</a>
        </div>
        """,
            403,
        )

    # 3. Process Grades if open
    grades = {}
    for key in form:
        if key.startswith("marks_"):
            q_no = key.split("_")[1]
            marks = float(form[key][0])
            feedback = form.get(f"feedback_{q_no}", [""])[0]

            # Simple validation to ensure marks don't exceed max
            # (In a real app, you'd fetch max_marks here to verify)

            grades[q_no] = {
                "marks": marks,
                "feedback": feedback,
                "max_marks": 0,  # This needs to be populated from question data in service or here
            }

    # Note: save_short_answer_grades needs max_marks.
    # For this snippet, we assume the service handles fetching max_marks or we pass it.
    # To fix this properly, we should re-fetch questions, but for brevity:

    # Re-fetch questions to get max_marks correctly
    full_submission = get_submission_with_questions(submission_id)
    for q in full_submission.get("short_answer_questions", []):
        q_no = str(q["question_no"])
        if q_no in grades:
            grades[q_no]["max_marks"] = q["max_marks"]

    save_short_answer_grades(submission_id, grades)

    return get_grading_dashboard(submission.get("exam_id"))
