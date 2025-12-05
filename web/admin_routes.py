from urllib.parse import parse_qs
import html
from datetime import datetime

from core.validation import validate_result_release_date
from services.exam_service import (
    get_all_published_exams_for_admin,
    get_exam_by_id,
    set_result_release_date,
    calculate_exam_statistics,
    finalize_exam_results,
)
from .template_engine import render
from core.firebase_db import db


def _parse_form(body: str) -> dict:
    """Parse form data from POST request"""
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    return {
        "exam_id": get_field("exam_id"),
        "release_date": get_field("release_date"),
        "release_time": get_field("release_time"),
    }


def _parse_grading_form(body: str) -> dict:
    """Parse grading settings form data"""
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    return {
        "exam_id": get_field("exam_id"),
        "grading_deadline_date": get_field("grading_deadline_date"),
        "grading_deadline_time": get_field("grading_deadline_time"),
        "release_date": get_field("release_date"),
        "release_time": get_field("release_time"),
    }


def get_admin_exam_list():
    """
    GET handler for admin exam list with result release date management
    Shows grading deadline status and result release status
    """
    all_exams = get_all_published_exams_for_admin()

    exam_list_html = ""

    if not all_exams:
        exam_list_html = """
        <div class="alert alert-info">
            <h5>No published exams found</h5>
            <p class="mb-0">Only published exams appear here for result management.</p>
        </div>
        """
    else:
        for exam in all_exams:
            e_id = exam.get("exam_id", "")
            title = html.escape(exam.get("title", "Untitled"))
            description = html.escape(exam.get("description", "No description"))
            duration = exam.get("duration", 0)
            exam_date = exam.get("exam_date", "N/A")

            # Get time information
            start_time = exam.get("start_time", "N/A")
            end_time = exam.get("end_time", "N/A")

            # ========================================
            # GRADING DEADLINE STATUS
            # ========================================
            grading_deadline = exam.get("grading_deadline_date", "")
            grading_time = exam.get("grading_deadline_time", "23:59")

            # Initialize flag to track if grading is allowed
            is_grading_closed = False

            if grading_deadline:
                try:
                    deadline_str = f"{grading_deadline} {grading_time}"
                    deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
                    now = datetime.now()

                    if now > deadline_dt:
                        grading_status = '<span class="badge bg-danger ms-2">🔒 Grading Closed</span>'
                        grading_display = (
                            f"Closed on {grading_deadline} at {grading_time}"
                        )
                        is_grading_closed = True
                    else:
                        # Calculate time remaining
                        time_remaining = deadline_dt - now
                        days_remaining = time_remaining.days
                        hours_remaining = time_remaining.seconds // 3600

                        if days_remaining == 0 and hours_remaining < 24:
                            grading_status = f'<span class="badge bg-danger ms-2">⏰ {hours_remaining}h Left</span>'
                        elif days_remaining < 2:
                            grading_status = f'<span class="badge bg-warning text-dark ms-2">⚠️ {days_remaining}d Left</span>'
                        else:
                            grading_status = f'<span class="badge bg-info ms-2">📅 {days_remaining}d Left</span>'

                        grading_display = (
                            f"Open until {grading_deadline} at {grading_time}"
                        )

                except ValueError:
                    grading_status = (
                        '<span class="badge bg-secondary ms-2">⚠️ Invalid Date</span>'
                    )
                    grading_display = (
                        f"{grading_deadline} at {grading_time} (Invalid format)"
                    )
            else:
                grading_status = (
                    '<span class="badge bg-secondary ms-2">No Deadline</span>'
                )
                grading_display = "Not set"

            # ========================================
            # RESULT RELEASE STATUS
            # ========================================
            release_date = exam.get("result_release_date", "")
            release_time = exam.get("result_release_time", "00:00")

            if release_date:
                try:
                    release_datetime_str = f"{release_date} {release_time}"
                    release_dt = datetime.strptime(
                        release_datetime_str, "%Y-%m-%d %H:%M"
                    )
                    now = datetime.now()

                    if now >= release_dt:
                        release_status = '<span class="badge bg-success ms-2">✅ Results Released</span>'
                    else:
                        release_status = '<span class="badge bg-warning text-dark ms-2">📆 Scheduled</span>'
                except ValueError:
                    release_status = (
                        '<span class="badge bg-secondary ms-2">⚠️ Invalid Date</span>'
                    )
            else:
                release_status = '<span class="badge bg-secondary ms-2">Not Set</span>'

            release_display = (
                f"{release_date} at {release_time}" if release_date else "Not set"
            )

            # ========================================
            # CHECK IF RESULTS ARE FINALIZED
            # ========================================
            is_finalized = exam.get("results_finalized", False)
            finalized_badge = ""
            if is_finalized:
                finalized_at = exam.get("finalized_at", "")
                if finalized_at and hasattr(finalized_at, "strftime"):
                    finalized_at_str = finalized_at.strftime("%Y-%m-%d %H:%M")
                else:
                    finalized_at_str = str(finalized_at)
                finalized_badge = f'<span class="badge bg-dark ms-2">🔐 Finalized on {finalized_at_str}</span>'
                # If finalized, grading is definitely closed regardless of deadline
                is_grading_closed = True

            # ========================================
            # BUILD EXAM CARD HTML
            # ========================================

            # Conditional Logic for Grading Button
            # If grading is closed, REMOVE the button entirely.
            if is_grading_closed:
                grade_button_html = ""
            else:
                grade_button_html = f"""
                <a href="/grade-submissions?exam_id={e_id}" 
                   class="btn btn-sm btn-success">
                   📝 Grade Submissions
                </a>
                """

            exam_list_html += f"""
            <div class="exam-card">
                <div class="exam-info">
                    <h5 class="exam-title">
                        {title}
                        <span class="exam-status status-published">Published</span>
                        {grading_status}
                        {release_status}
                        {finalized_badge}
                    </h5>
                    <p class="exam-desc">{description}</p>
                    
                    <div class="exam-meta">
                        <span>📅 Exam: {exam_date}</span>
                        <span>🕐 {start_time} - {end_time}</span>
                        <span>⏱️ {duration} mins</span>
                        <span class="exam-id">ID: {e_id}</span>
                    </div>
                    
                    <div class="exam-meta mt-2 p-2 bg-light rounded">
                        <div><strong>⏰ Grading Deadline:</strong> {grading_display}</div>
                        <div class="mt-1"><strong>📊 Result Release:</strong> {release_display}</div>
                    </div>
                </div>
                
                <div class="exam-actions d-flex flex-column gap-2">
                    <a href="/admin/grading-settings?exam_id={e_id}" 
                       class="btn btn-sm btn-primary">
                       ⚙️ Settings
                    </a>
                    
                    {grade_button_html}
                    
                    {"" if is_finalized else f'''
                    <a href="/admin/finalize-exam?exam_id={e_id}" 
                       class="btn btn-sm btn-warning">
                       🔒 Finalize Results
                    </a>
                    '''}
                </div>
            </div>
            """

    html_str = render("admin_exam_list.html", {"exam_list_html": exam_list_html})
    return html_str, 200


def get_set_result_release(exam_id: str):
    """
    GET handler for setting result release date
    DEPRECATED: Use get_grading_settings instead
    """
    if not exam_id:
        html_str = render(
            "set_result_release.html",
            {
                "exam_id": "",
                "title": "",
                "exam_date": "",
                "release_date": "",
                "release_time": "00:00",
                "errors_html": "",
                "success_html": "",
            },
        )
        return html_str, 400

    exam = get_exam_by_id(exam_id)

    if not exam:
        html_str = render(
            "set_result_release.html",
            {
                "exam_id": exam_id,
                "title": "Exam not found",
                "exam_date": "",
                "release_date": "",
                "release_time": "00:00",
                "errors_html": f'<div class="alert alert-danger">Exam "{exam_id}" not found.</div>',
                "success_html": "",
            },
        )
        return html_str, 404

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "exam_date": exam.get("exam_date", ""),
        "start_time": exam.get("start_time", ""),
        "end_time": exam.get("end_time", ""),
        "release_date": exam.get("result_release_date", ""),
        "release_time": exam.get("result_release_time", "00:00"),
        "errors_html": "",
        "success_html": "",
    }

    html_str = render("set_result_release.html", ctx)
    return html_str, 200


def post_set_result_release(body: str):
    """
    POST handler for setting result release date
    DEPRECATED: Use post_grading_settings instead
    """
    form = _parse_form(body)
    exam_id = form.get("exam_id")

    if not exam_id:
        ctx = dict(form)
        ctx["errors_html"] = (
            '<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam ID is missing.</div>'
        )
        ctx["success_html"] = ""
        ctx["title"] = ""
        ctx["exam_date"] = ""
        html_str = render("set_result_release.html", ctx)
        return html_str, 400

    # Get exam to validate
    exam = get_exam_by_id(exam_id)
    if not exam:
        ctx = dict(form)
        ctx["errors_html"] = (
            f'<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam "{exam_id}" not found.</div>'
        )
        ctx["success_html"] = ""
        ctx["title"] = ""
        ctx["exam_date"] = ""
        html_str = render("set_result_release.html", ctx)
        return html_str, 404

    # Validation
    errors = validate_result_release_date(form["release_date"], exam.get("exam_date"))

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
        ctx["success_html"] = ""
        ctx["title"] = exam.get("title", "")
        ctx["exam_date"] = exam.get("exam_date", "")
        ctx["description"] = exam.get("description", "")
        ctx["start_time"] = exam.get("start_time", "")
        ctx["end_time"] = exam.get("end_time", "")
        html_str = render("set_result_release.html", ctx)
        return html_str, 400

    # Save result release date
    try:
        set_result_release_date(
            exam_id=exam_id,
            release_date=form["release_date"],
            release_time=form["release_time"],
        )

        success_html = """
        <div class="alert alert-success mb-3">
            <strong>Success!</strong> Result release date has been set.
            <a href="/admin/exam-list" class="alert-link">Return to exam list</a>
        </div>
        """
        ctx = dict(form)
        ctx["success_html"] = success_html
        ctx["errors_html"] = ""
        ctx["title"] = exam.get("title", "")
        ctx["exam_date"] = exam.get("exam_date", "")
        ctx["description"] = exam.get("description", "")
        ctx["start_time"] = exam.get("start_time", "")
        ctx["end_time"] = exam.get("end_time", "")
        html_str = render("set_result_release.html", ctx)
        return html_str, 200

    except ValueError as e:
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Error:</strong> {html.escape(str(e))}
        </div>
        """
        ctx = dict(form)
        ctx["errors_html"] = errors_html
        ctx["success_html"] = ""
        ctx["title"] = exam.get("title", "")
        ctx["exam_date"] = exam.get("exam_date", "")
        ctx["description"] = exam.get("description", "")
        ctx["start_time"] = exam.get("start_time", "")
        ctx["end_time"] = exam.get("end_time", "")
        html_str = render("set_result_release.html", ctx)
        return html_str, 500


# ============================================================
# NEW: COMPREHENSIVE GRADING SETTINGS
# ============================================================


def get_grading_settings(exam_id: str):
    """
    GET handler for comprehensive grading and release settings
    Combines grading deadline and result release in one interface
    """
    if not exam_id:
        error_ctx = {
            "exam_id": "",
            "title": "Error",
            "exam_date": "",
            "exam_end_time": "",
            "grading_deadline_date": "",
            "grading_deadline_time": "23:59",
            "release_date": "",
            "release_time": "00:00",
            "errors_html": '<div class="alert alert-danger">Missing exam ID</div>',
            "success_html": "",
        }
        html_str = render("admin_grading_setting.html", error_ctx)
        return html_str, 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        error_ctx = {
            "exam_id": exam_id,
            "title": "Exam Not Found",
            "exam_date": "",
            "exam_end_time": "",
            "grading_deadline_date": "",
            "grading_deadline_time": "23:59",
            "release_date": "",
            "release_time": "00:00",
            "errors_html": f'<div class="alert alert-danger">Exam "{html.escape(exam_id)}" not found.</div>',
            "success_html": "",
        }
        html_str = render("admin_grading_setting.html", error_ctx)
        return html_str, 404

    ctx = {
        "exam_id": exam.get("exam_id"),
        "title": exam.get("title", ""),
        "exam_date": exam.get("exam_date", ""),
        "exam_end_time": exam.get("end_time", ""),
        # Grading deadline
        "grading_deadline_date": exam.get("grading_deadline_date", ""),
        "grading_deadline_time": exam.get("grading_deadline_time", "23:59"),
        # Result release
        "release_date": exam.get("result_release_date", ""),
        "release_time": exam.get("result_release_time", "00:00"),
        "errors_html": "",
        "success_html": "",
    }

    html_str = render("admin_grading_setting.html", ctx)
    return html_str, 200


def post_grading_settings(body: str):
    """
    POST handler to save grading deadline and result release settings
    Performs comprehensive validation
    """
    from core.validation import validate_grading_periods
    from services.exam_service import save_grading_settings

    form = _parse_grading_form(body)
    exam_id = form.get("exam_id")

    if not exam_id:
        error_ctx = dict(form)
        error_ctx["errors_html"] = (
            '<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam ID is missing.</div>'
        )
        error_ctx["success_html"] = ""
        error_ctx["title"] = ""
        error_ctx["exam_date"] = ""
        error_ctx["exam_end_time"] = ""
        html_str = render("admin_grading_setting.html", error_ctx)
        return html_str, 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        error_ctx = dict(form)
        error_ctx["errors_html"] = (
            f'<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam "{html.escape(exam_id)}" not found.</div>'
        )
        error_ctx["success_html"] = ""
        error_ctx["title"] = ""
        error_ctx["exam_date"] = ""
        error_ctx["exam_end_time"] = ""
        html_str = render("admin_grading_setting.html", error_ctx)
        return html_str, 404

    # VALIDATION
    errors = validate_grading_periods(
        exam_date=exam.get("exam_date"),
        exam_end_time=exam.get("end_time"),
        grading_deadline_date=form["grading_deadline_date"],
        grading_deadline_time=form["grading_deadline_time"],
        release_date=form["release_date"],
        release_time=form["release_time"],
    )

    if errors:
        error_items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>⚠️ Please fix the following:</strong>
            <ul class="mb-0 mt-2">{error_items}</ul>
        </div>
        """
        ctx = dict(form)
        ctx["errors_html"] = errors_html
        ctx["success_html"] = ""
        ctx["title"] = exam.get("title", "")
        ctx["exam_date"] = exam.get("exam_date", "")
        ctx["exam_end_time"] = exam.get("end_time", "")
        html_str = render("admin_grading_setting.html", ctx)
        return html_str, 400

    # SAVE to Firebase
    try:
        save_grading_settings(
            exam_id=exam_id,
            grading_deadline_date=form["grading_deadline_date"],
            grading_deadline_time=form["grading_deadline_time"],
            release_date=form["release_date"],
            release_time=form["release_time"],
        )

        success_html = """
        <div class="alert alert-success mb-3">
            <h5 class="alert-heading">✅ Settings Saved Successfully!</h5>
            <hr>
            <p class="mb-0">
                Grading deadline and result release dates have been configured.
                <a href="/admin/exam-list" class="alert-link fw-bold">Return to exam list</a>
            </p>
        </div>
        """
        ctx = dict(form)
        ctx["success_html"] = success_html
        ctx["errors_html"] = ""
        ctx["title"] = exam.get("title", "")
        ctx["exam_date"] = exam.get("exam_date", "")
        ctx["exam_end_time"] = exam.get("end_time", "")
        html_str = render("admin_grading_setting.html", ctx)
        return html_str, 200

    except ValueError as e:
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>❌ Error saving settings:</strong><br>
            {html.escape(str(e))}
        </div>
        """
        ctx = dict(form)
        ctx["errors_html"] = errors_html
        ctx["success_html"] = ""
        ctx["title"] = exam.get("title", "")
        ctx["exam_date"] = exam.get("exam_date", "")
        ctx["exam_end_time"] = exam.get("end_time", "")
        html_str = render("admin_grading_setting.html", ctx)
        return html_str, 500


def get_ungraded_submissions(exam_id: str) -> list:
    """
    Get all submissions that still need grading

    Args:
        exam_id: Exam identifier

    Returns:
        List of ungraded submission dictionaries
    """
    submissions_query = (
        db.collection("submissions").where("exam_id", "==", exam_id).stream()
    )

    ungraded = []
    for doc in submissions_query:
        sub = doc.to_dict()
        sub["submission_id"] = doc.id

        # Check if fully graded
        if not sub.get("mcq_graded") or not sub.get("sa_graded"):
            ungraded.append(sub)

    return ungraded


def get_all_exam_submissions(exam_id: str) -> list:
    """Get all submissions for an exam"""
    submissions_query = (
        db.collection("submissions").where("exam_id", "==", exam_id).stream()
    )

    submissions = []
    for doc in submissions_query:
        sub = doc.to_dict()
        sub["submission_id"] = doc.id
        submissions.append(sub)

    return submissions


def get_finalize_exam(exam_id: str):
    """
    GET handler for finalization confirmation page
    Shows statistics and checks if exam is ready to finalize
    """
    if not exam_id:
        error_html = """
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Error</h4>
                <p>Missing exam ID</p>
                <a href="/admin/exam-list" class="btn btn-secondary">Back to Exam List</a>
            </div>
        </div>
        """
        return error_html, 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        error_html = f"""
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Error</h4>
                <p>Exam "{html.escape(exam_id)}" not found</p>
                <a href="/admin/exam-list" class="btn btn-secondary">Back to Exam List</a>
            </div>
        </div>
        """
        return error_html, 404

    # Check if already finalized
    if exam.get("results_finalized"):
        finalized_at = exam.get("finalized_at", "")
        if finalized_at and hasattr(finalized_at, "strftime"):
            finalized_at_str = finalized_at.strftime("%Y-%m-%d %H:%M")
        else:
            finalized_at_str = str(finalized_at)

        info_html = f"""
        <div class="container mt-5">
            <div class="alert alert-info">
                <h4>ℹ️ Already Finalized</h4>
                <p>This exam was finalized on <strong>{finalized_at_str}</strong></p>
                <p>Results are locked and cannot be changed.</p>
                <a href="/admin/exam-list" class="btn btn-primary">Back to Exam List</a>
            </div>
        </div>
        """
        return info_html, 200

    # Get all submissions
    all_submissions = get_all_exam_submissions(exam_id)
    ungraded = get_ungraded_submissions(exam_id)

    # Calculate statistics
    if all_submissions:
        stats = calculate_exam_statistics(all_submissions)
    else:
        stats = {
            "total_students": 0,
            "average_percentage": 0,
            "highest_score": 0,
            "lowest_score": 0,
            "pass_rate": 0,
            "grade_distribution": {},
        }

    # Check if can finalize
    can_finalize = len(ungraded) == 0 and len(all_submissions) > 0

    # Build warning/error messages
    warning_html = ""
    if not all_submissions:
        warning_html = """
        <div class="alert alert-danger">
            <h5>❌ Cannot Finalize</h5>
            <p>No submissions found for this exam. Students must complete the exam first.</p>
        </div>
        """
    elif ungraded:
        ungraded_list = ""
        for sub in ungraded[:10]:  # Show first 10
            student_id = sub.get("student_id", "Unknown")
            status = []
            if not sub.get("mcq_graded"):
                status.append("MCQ pending")
            if not sub.get("sa_graded"):
                status.append("Short answers pending")
            ungraded_list += f"<li><strong>{html.escape(student_id)}</strong>: {', '.join(status)}</li>"

        if len(ungraded) > 10:
            ungraded_list += f"<li><em>... and {len(ungraded) - 10} more</em></li>"

        warning_html = f"""
        <div class="alert alert-warning">
            <h5>⚠️ Cannot Finalize Yet</h5>
            <p><strong>{len(ungraded)}</strong> submission(s) still need grading:</p>
            <ul class="mb-0">{ungraded_list}</ul>
            <hr>
            <a href="/grade-submissions?exam_id={exam_id}" class="btn btn-primary mt-2">
                Go to Grading Interface
            </a>
        </div>
        """

    # Build statistics display
    grade_dist = stats.get("grade_distribution", {})
    grade_dist_html = ""
    for grade, count in grade_dist.items():
        percentage = (
            (count / stats["total_students"] * 100)
            if stats["total_students"] > 0
            else 0
        )
        grade_dist_html += f"""
        <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-secondary">{grade}</span>
            <div class="progress flex-grow-1 mx-3" style="height: 25px;">
                <div class="progress-bar bg-primary" style="width: {percentage}%">
                    {count} students
                </div>
            </div>
            <span>{percentage:.1f}%</span>
        </div>
        """

    stats_html = f"""
    <div class="row g-3 mb-4">
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-primary">{stats['total_students']}</h3>
                    <p class="text-muted mb-0">Total Students</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-success">{stats['average_percentage']:.1f}%</h3>
                    <p class="text-muted mb-0">Average Score</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-info">{stats['highest_score']:.1f}%</h3>
                    <p class="text-muted mb-0">Highest Score</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h3 class="text-warning">{stats['pass_rate']:.1f}%</h3>
                    <p class="text-muted mb-0">Pass Rate</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card mb-4">
        <div class="card-header">
            <h5 class="mb-0">📊 Grade Distribution</h5>
        </div>
        <div class="card-body">
            {grade_dist_html if grade_dist_html else '<p class="text-muted">No data available</p>'}
        </div>
    </div>
    """

    # Build action buttons
    if can_finalize:
        action_html = f"""
        <form method="POST" action="/admin/finalize-exam-confirm" 
              onsubmit="return confirm('⚠️ IMPORTANT: Once finalized, grades CANNOT be changed.\\n\\nAre you sure you want to finalize this exam?');">
            <input type="hidden" name="exam_id" value="{exam_id}">
            <input type="hidden" name="admin_id" value="admin">
            <div class="d-flex gap-3 justify-content-center">
                <a href="/admin/exam-list" class="btn btn-secondary btn-lg px-5">Cancel</a>
                <button type="submit" class="btn btn-danger btn-lg px-5">
                    🔒 Finalize & Lock Results
                </button>
            </div>
        </form>
        """
    else:
        action_html = f"""
        <div class="text-center">
            <a href="/grade-submissions?exam_id={exam_id}" class="btn btn-primary btn-lg px-5">
                📝 Complete Grading First
            </a>
        </div>
        """

    ctx = {
        "exam_id": exam_id,
        "exam_title": exam.get("title", ""),
        "warning_html": warning_html,
        "stats_html": stats_html,
        "action_html": action_html,
        "can_finalize": can_finalize,
    }

    html_str = render("finalize_exam.html", ctx)
    return html_str, 200


def post_finalize_exam(body: str):
    """
    POST handler to execute finalization
    This permanently locks all grading
    """
    from urllib.parse import parse_qs

    data = parse_qs(body)
    exam_id = data.get("exam_id", [""])[0]
    admin_id = data.get("admin_id", ["admin"])[0]

    if not exam_id:
        error_html = """
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Error</h4>
                <p>Missing exam ID</p>
                <a href="/admin/exam-list" class="btn btn-secondary">Back</a>
            </div>
        </div>
        """
        return error_html, 400

    try:
        # Execute finalization
        result = finalize_exam_results(exam_id, admin_id)

        success_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Finalization Complete</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="/static/styles.css">
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="alert alert-success">
                    <h2>✅ Exam Results Finalized Successfully!</h2>
                    <hr>
                    <h5>Summary:</h5>
                    <ul>
                        <li><strong>Total Students:</strong> {result['total_students']}</li>
                        <li><strong>Average Score:</strong> {result['average_score']:.2f}%</li>
                        <li><strong>Pass Rate:</strong> {result['pass_rate']:.2f}%</li>
                        <li><strong>Finalized At:</strong> {result['finalized_at'].strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <hr>
                    <p class="mb-0">
                        <strong>🔒 All grades are now PERMANENTLY LOCKED.</strong><br>
                        Students will be able to view their results according to the release schedule.
                    </p>
                </div>
                <div class="text-center">
                    <a href="/admin/exam-list" class="btn btn-primary btn-lg">Return to Exam List</a>
                </div>
            </div>
        </body>
        </html>
        """
        return success_html, 200

    except ValueError as e:
        error_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Finalization Error</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="alert alert-danger">
                    <h4>❌ Cannot Finalize Exam</h4>
                    <p><strong>Error:</strong> {html.escape(str(e))}</p>
                    <hr>
                    <a href="/admin/finalize-exam?exam_id={exam_id}" class="btn btn-secondary">Go Back</a>
                </div>
            </div>
        </body>
        </html>
        """
        return error_html, 400

    except Exception as e:
        error_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>System Error</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="alert alert-danger">
                    <h4>💥 System Error</h4>
                    <p><strong>Unexpected error:</strong> {html.escape(str(e))}</p>
                    <p>Please contact the system administrator.</p>
                    <hr>
                    <a href="/admin/exam-list" class="btn btn-secondary">Return to Exam List</a>
                </div>
            </div>
        </body>
        </html>
        """
        return error_html, 500
