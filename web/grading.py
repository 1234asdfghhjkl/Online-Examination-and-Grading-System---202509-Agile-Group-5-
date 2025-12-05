"""
Created on 2024-11-27
By Liyi
Teacher Grading Interface
Handles teacher grading of short answer questions
"""

import html
from urllib.parse import parse_qs

from web.template_engine import render
from services.exam_service import (
    get_exam_by_id,
    check_grading_locked,
)  # Added check_grading_locked
from services.short_answer_grading_service import (
    get_all_submissions_for_exam,
    get_submission_with_questions,
    save_short_answer_grades,
)


def get_grade_submissions(exam_id: str):
    """
    GET handler for viewing all submissions for an exam
    """
    if not exam_id:
        message_html = """
        <div class="alert alert-danger">
            Missing exam ID
        </div>
        """
        html_str = render(
            "grade_submissions.html",
            {
                "exam_id": "",
                "exam_title": "",
                "message_html": message_html,
                "submissions_list_html": "",
            },
        )
        return html_str, 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        message_html = f"""
        <div class="alert alert-danger">
            Exam {html.escape(exam_id)} not found
        </div>
        """
        html_str = render(
            "grade_submissions.html",
            {
                "exam_id": exam_id,
                "exam_title": "",
                "message_html": message_html,
                "submissions_list_html": "",
            },
        )
        return html_str, 404

    # --- DEADLINE CHECK START ---
    is_locked, lock_msg, _ = check_grading_locked(exam_id)

    lock_alert_html = ""
    if is_locked:
        lock_alert_html = f"""
        <div class="alert alert-danger mb-4">
            <h5 class="alert-heading">🔒 {html.escape(lock_msg)}</h5>
            <p class="mb-0">The grading period has ended. You can view submissions but <strong>cannot make changes</strong>.</p>
        </div>
        """
    # --- DEADLINE CHECK END ---

    submissions = get_all_submissions_for_exam(exam_id)

    if not submissions:
        submissions_list_html = """
        <div class="alert alert-info">
            No submissions yet for this exam.
        </div>
        """
    else:
        submissions_list_html = ""
        for sub in submissions:
            student_id = sub.get("student_id", "Unknown")
            submission_id = sub.get("submission_id")
            submitted_at = sub.get("submitted_at")

            if submitted_at:
                submitted_time = submitted_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                submitted_time = "N/A"

            mcq_score = sub.get("mcq_score", 0)
            mcq_total = sub.get("mcq_total", 0)
            sa_obtained = sub.get("sa_obtained_marks", 0)
            sa_total = sub.get("sa_total_marks", 0)

            # Grading status
            mcq_graded = sub.get("mcq_graded", False)
            sa_graded = sub.get("sa_graded", False)
            fully_graded = sub.get("fully_graded", False)

            # --- BUTTON LOGIC UPDATE ---
            if is_locked:
                # If locked, only show a View button regardless of status
                action_btn = f"""
                <a href="/grade-short-answers?submission_id={submission_id}" 
                   class="btn btn-sm btn-secondary">
                    🔒 View (Locked)
                </a>
                """
            else:
                # Normal logic
                if fully_graded:
                    status_badge = (
                        '<span class="status-badge graded">✅ Fully Graded</span>'
                    )
                    action_btn = """
                    <a href="" class="btn btn-sm btn-outline-success">View Results</a>
                    """
                elif sa_graded:
                    status_badge = (
                        '<span class="status-badge graded">✅ SA Graded</span>'
                    )
                    action_btn = f"""
                    <a href="/grade-short-answers?submission_id={submission_id}" 
                       class="btn btn-sm btn-outline-primary">
                        Review Grading
                    </a>
                    """
                elif mcq_graded:
                    status_badge = (
                        '<span class="status-badge pending">⏳ SA Pending</span>'
                    )
                    action_btn = f"""
                    <a href="/grade-short-answers?submission_id={submission_id}" 
                       class="btn btn-sm btn-primary">
                        Grade Short Answers
                    </a>
                    """
                else:
                    status_badge = (
                        '<span class="status-badge pending">⏳ Pending</span>'
                    )
                    action_btn = f"""
                    <a href="/grade-short-answers?submission_id={submission_id}" 
                       class="btn btn-sm btn-primary">
                        Start Grading
                    </a>
                    """

            submissions_list_html += f"""
            <div class="submission-card">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h6 class="mb-2">
                            <strong>Student:</strong> {html.escape(student_id)}
                            {status_badge if not is_locked else '<span class="badge bg-secondary">Read Only</span>'}
                        </h6>
                        <div class="text-muted small">
                            <div>📅 Submitted: {submitted_time}</div>
                            <div class="mt-1">
                                <span class="me-3">MCQ: {mcq_score}/{mcq_total}</span>
                                <span>Short Answer: {sa_obtained}/{sa_total}</span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 text-end">
                        {action_btn}
                    </div>
                </div>
            </div>
            """

    html_str = render(
        "grade_submissions.html",
        {
            "exam_id": exam_id,
            "exam_title": exam.get("title", ""),
            "message_html": lock_alert_html,  # Pass the alert here
            "submissions_list_html": submissions_list_html,
        },
    )
    return html_str, 200


def get_grade_short_answers(submission_id: str):
    """
    GET handler for grading short answers for a specific submission
    """
    if not submission_id:
        # ... [Keep existing error handling] ...
        return "Missing submission ID", 400

    submission = get_submission_with_questions(submission_id)
    if not submission:
        # ... [Keep existing error handling] ...
        return "Submission not found", 404

    exam_id = submission.get("exam_id")
    exam = get_exam_by_id(exam_id)

    # --- DEADLINE CHECK START ---
    is_locked, lock_msg, _ = check_grading_locked(exam_id)

    # Define attributes for read-only mode
    disabled_attr = "disabled" if is_locked else ""
    readonly_class = "bg-light" if is_locked else ""
    # --- DEADLINE CHECK END ---

    # Build questions HTML
    questions_html = ""
    sa_questions = submission.get("short_answer_questions", [])
    existing_grades = submission.get("short_answer_grades", {})

    for q in sa_questions:
        q_no = q.get("question_no")
        question_text = q.get("question_text", "")
        sample_answer = q.get("sample_answer", "")
        student_answer = q.get("student_answer", "")
        max_marks = q.get("max_marks", 0)

        existing_grade = existing_grades.get(str(q_no), {})
        awarded_marks = existing_grade.get("marks", 0)
        feedback = existing_grade.get("feedback", "")

        questions_html += f"""
        <div class="grading-card">
            <h5>Question {q_no} ({max_marks} marks)</h5>
            <div><strong>Question:</strong> {html.escape(question_text)}</div>
            
            {f'''
            <div class="sample-answer mt-3">
                <strong>📝 Sample Answer (Reference):</strong>
                <div class="mt-2">{html.escape(sample_answer)}</div>
            </div>
            ''' if sample_answer else ''}
            
            <div class="student-answer mt-3">
                <strong>✍️ Student's Answer:</strong>
                <div class="mt-2">
                    {html.escape(student_answer) if student_answer else '<em class="text-muted">No answer provided</em>'}
                </div>
            </div>
            
            <div class="answer-section mt-3">
                <div class="marks-input-group">
                    <label for="marks_{q_no}" class="form-label mb-0">
                        <strong>Marks Awarded:</strong>
                    </label>
                    <input type="number" 
                           class="form-control marks-input {readonly_class}" 
                           id="marks_{q_no}"
                           name="marks_{q_no}" 
                           min="0" 
                           max="{max_marks}" 
                           step="0.5"
                           value="{awarded_marks}"
                           required
                           {disabled_attr}> 
                    <span class="text-muted">/ {max_marks}</span>
                    <input type="hidden" name="max_marks_{q_no}" value="{max_marks}">
                </div>
                
                <div class="mt-3">
                    <label for="feedback_{q_no}" class="form-label">
                        <strong>Feedback (Optional):</strong>
                    </label>
                    <textarea class="form-control {readonly_class}" 
                              id="feedback_{q_no}"
                              name="feedback_{q_no}" 
                              rows="3"
                              placeholder="Provide feedback to the student..."
                              {disabled_attr}>{html.escape(feedback)}</textarea>
                </div>
            </div>
        </div>
        """

    # --- SAVE BUTTON LOGIC ---
    if is_locked:
        message_html = f"""
        <div class="alert alert-danger sticky-top shadow-sm">
            <strong>🔒 {html.escape(lock_msg)}</strong>. Grading is disabled.
        </div>
        """
        # We can hide the save button by injecting a style or script,
        # but for this template structure, we might need to rely on the disabled inputs
        # and maybe add a script to hide the submit button if possible,
        # or just accept that the button exists but does nothing (backend protection).
        # Assuming the template renders a "Save Grades" button at the bottom:
        # Since I can't edit the HTML template file here, relying on disabled inputs + backend check is best.
    else:
        message_html = ""

    mcq_score = submission.get("mcq_score", 0)
    mcq_total = submission.get("mcq_total", 0)
    sa_obtained = submission.get("sa_obtained_marks", 0)
    sa_total = submission.get("sa_total_marks", 0)

    html_str = render(
        "grade_short_answers.html",
        {
            "submission_id": submission_id,
            "exam_id": exam_id,
            "exam_title": exam.get("title", "") if exam else "",
            "student_id": submission.get("student_id", ""),
            "mcq_score": mcq_score,
            "mcq_total": mcq_total,
            "sa_score": sa_obtained,
            "sa_total": sa_total,
            "message_html": message_html,
            "questions_html": questions_html,
        },
    )

    # Quick fix to hide submit button via CSS if locked
    if is_locked:
        html_str = html_str.replace(
            "</head>",
            '<style>button[type="submit"] { display: none !important; }</style></head>',
        )

    return html_str, 200


def post_save_short_answer_grades(body: str):
    """
    POST handler for saving short answer grades
    """
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    submission_id = get_field("submission_id")

    if not submission_id:
        return "<h1>Error: Missing submission ID</h1>", 400

    submission = get_submission_with_questions(submission_id)
    if not submission:
        return "<h1>Error: Submission not found</h1>", 404

    # --- SECURITY CHECK ---
    exam_id = submission.get("exam_id")
    is_locked, lock_msg, _ = check_grading_locked(exam_id)

    if is_locked:
        return (
            f"""
        <div style="padding: 20px; color: #721c24; background: #f8d7da; border: 1px solid #f5c6cb;">
            <h2>⛔ Grading Rejected</h2>
            <p><strong>{html.escape(lock_msg)}</strong></p>
            <p>You cannot save grades after the deadline.</p>
            <a href="/grade-submissions?exam_id={exam_id}">Back to Submissions</a>
        </div>
        """,
            403,
        )
    # --- END SECURITY CHECK ---

    # Parse grades
    grades = {}
    sa_questions = submission.get("short_answer_questions", [])

    for q in sa_questions:
        q_no = str(q.get("question_no"))
        marks_key = f"marks_{q_no}"
        feedback_key = f"feedback_{q_no}"
        max_marks_key = f"max_marks_{q_no}"

        marks = float(get_field(marks_key) or 0)
        feedback = get_field(feedback_key)
        max_marks = float(get_field(max_marks_key) or 0)

        grades[q_no] = {"marks": marks, "max_marks": max_marks, "feedback": feedback}

    # Save grades
    try:
        save_short_answer_grades(submission_id, grades)
    except Exception as e:
        return f"<h1>Error saving grades: {html.escape(str(e))}</h1>", 500

    # Redirect back to submissions list
    redirect_html = f"""
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url=/grade-submissions?exam_id={html.escape(exam_id)}">
      </head>
      <body>
        <p>Grades saved successfully! Redirecting...</p>
      </body>
    </html>
    """
    return redirect_html, 200
