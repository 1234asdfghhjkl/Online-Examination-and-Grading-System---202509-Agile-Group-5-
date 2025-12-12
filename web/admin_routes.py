from urllib.parse import parse_qs
import html
import json
from datetime import datetime
from typing import Optional
from services.user_service import parse_excel_data, bulk_create_users
from core.validation import validate_result_release_date, validate_grading_periods
from services.exam_service import (
    get_all_published_exams_for_admin,
    get_exam_by_id,
    set_result_release_date,
    save_grading_settings,
)
from web.template_engine import render
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
                            grading_status = f'<span class="badge bg-danger ms-2">⚠️ {hours_remaining}h Left</span>'
                        elif days_remaining < 2:
                            grading_status = f'<span class="badge bg-warning text-dark ms-2">⏰ {days_remaining}d Left</span>'
                        else:
                            grading_status = f'<span class="badge bg-info ms-2">✓ {days_remaining}d Left</span>'

                        grading_display = (
                            f"Open until {grading_deadline} at {grading_time}"
                        )

                except ValueError:
                    grading_status = (
                        '<span class="badge bg-secondary ms-2">❌ Invalid Date</span>'
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
                        release_status = '<span class="badge bg-warning text-dark ms-2">📅 Scheduled</span>'
                except ValueError:
                    release_status = (
                        '<span class="badge bg-secondary ms-2">❌ Invalid Date</span>'
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
                finalized_badge = f'<span class="badge bg-dark ms-2">✓ Finalized on {finalized_at_str}</span>'
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
                   Grade Submissions
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
                        <div class="mt-1"><strong>📅 Result Release:</strong> {release_display}</div>
                    </div>
                </div>

                <div class="exam-actions d-flex flex-column gap-2">
                    <a href="/admin/grading-settings?exam_id={e_id}"
                       class="btn btn-sm btn-primary">
                       ⚙️ Settings
                    </a>

                    {grade_button_html}
                    
                    <a href="/admin/performance-report?exam_id={e_id}"
                       class="btn btn-sm btn-info">
                       📊 View Performance
                    </a>
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
                "description": "",
                "exam_date": "",
                "start_time": "",
                "end_time": "",
                "release_date": "",
                "release_time": "00:00",
                "errors_html": '<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam ID is missing.</div>',
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
                "title": "",
                "description": "",
                "exam_date": "",
                "start_time": "",
                "end_time": "",
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
        ctx["description"] = ""
        ctx["exam_date"] = ""
        ctx["start_time"] = ""
        ctx["end_time"] = ""
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
        ctx["description"] = ""
        ctx["exam_date"] = ""
        ctx["start_time"] = ""
        ctx["end_time"] = ""
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
            <strong> Please fix the following:</strong>
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
            <h5 class="alert-heading"> Settings Saved Successfully!</h5>
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
            <strong> Error saving settings:</strong><br>
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


# ============================================================
# NEW: ACCOUNT IMPORT/CREATION ROUTES
# ============================================================


def get_account_import_page():
    """
    GET handler for the account import page
    """
    ctx = {
        "success_html": "",
        "errors_html": "",
        "max_file_size": "2MB",  # Display limit
    }
    html_str = render("admin_account_import.html", ctx)
    return html_str, 200


def post_import_accounts(
    user_type: str,
    form_fields: dict[str, str],
    file_content: Optional[bytes],
    file_name: Optional[str],
):
    """
    POST handler to process uploaded Excel data for account creation.

    Args:
        user_type: 'lecturer' or 'student'.
        form_fields: Dictionary of non-file form fields (parsed by server.py).
        file_content: Bytes of the uploaded file.
        file_name: The name of the uploaded file.
    """

    ctx = {
        "success_html": "",
        "errors_html": "",
        "max_file_size": "2MB",
    }

    # 1. Validation Check: Was a file actually provided?
    if not file_name or file_name.strip() == "":
        ctx[
            "errors_html"
        ] = """
        <div class="alert alert-danger">
            <strong>Upload Failed:</strong> Please select an Excel file for import.
        </div>
        """
        html_str = render("admin_account_import.html", ctx)
        return html_str, 400

    if not file_content:
        ctx[
            "errors_html"
        ] = """
        <div class="alert alert-danger">
            <strong>Upload Failed:</strong> File content was empty or unreadable by the server.
        </div>
        """
        html_str = render("admin_account_import.html", ctx)
        return html_str, 400

    # --- REAL CREATION LOGIC ---
    user_type_display = user_type.title()

    try:
        # 2. Parse Excel data
        users_list = parse_excel_data(file_content, user_type)

        # 3. Bulk create users in Firebase Auth & Firestore
        stats = bulk_create_users(users_list, user_type)

        # 4. Success / Report

        summary_items = []
        if stats["created"] > 0:
            summary_items.append(
                f"Successfully **Created** {stats['created']} new {user_type_display} accounts."
            )

        if stats["failed"] > 0:
            summary_items.append(
                f"**Failed** to create {stats['failed']} {user_type_display} accounts due to Firebase errors."
            )

            # Detailed error list
            error_list_html = "".join(
                f"<li>{html.escape(e)}</li>" for e in stats["errors"]
            )
            error_section = f"""
            <h6 class="mt-3">Detailed Errors:</h6>
            <ul class="mb-0 small text-danger">
                {error_list_html}
            </ul>
            """
        else:
            error_section = ""

        success_html = f"""
        <div class="alert alert-success">
            <h5>✅ Account Import Successful!</h5>
            <p>Processed **{stats['total']}** records from **{html.escape(file_name)}**.</p>
            <ul>
                {"".join(f"<li>{item}</li>" for item in summary_items)}
            </ul>
            {error_section if stats['failed'] > 0 else ""}
        </div>
        """
        ctx["success_html"] = success_html
        return render("admin_account_import.html", ctx), 200

    except Exception as e:
        # Handle parsing errors or critical service errors
        error_message = f"Critical Import Error: {html.escape(str(e))}"

        # Check if the error is a missing column/format issue
        if "Missing required columns" in str(e) or "No valid user records found" in str(
            e
        ):
            error_message = f"File Format Error: {html.escape(str(e))}"

        errors_html = f"""
        <div class="alert alert-danger">
            <h5>❌ Import Failed!</h5>
            <p class="mb-0">**Reason:** {error_message}</p>
            <p class="mb-0 mt-2">Please ensure the file is a valid Excel (XLSX) and follows the specified format.</p>
        </div>
        """
        ctx["errors_html"] = errors_html
        return render("admin_account_import.html", ctx), 400


# ------- Deactivate student / lecturer account ---------
def deactivate_student_handler(request_body_json):
    try:
        student_id = request_body_json.get("student_id")

        if not student_id:
            return (
                json.dumps({"success": False, "message": "Student ID is required"}),
                400,
            )

        users_ref = db.collection("users")
        query = users_ref.where("student_id", "==", student_id).limit(1)
        docs = list(query.stream())

        if not docs:
            return (
                json.dumps(
                    {"success": False, "message": f"Student {student_id} not found"}
                ),
                404,
            )

        doc_ref = docs[0].reference
        doc_ref.update({"is_active": False, "status": "inactive"})

        return (
            json.dumps(
                {
                    "success": True,
                    "message": f"Student {student_id} has been deactivated successfully.",
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error deactivating student: {e}")
        return json.dumps({"success": False, "message": "Server Error"}), 500


def deactivate_lecturer_handler(request_body_json):
    try:
        lecturer_id = request_body_json.get("lecturer_id")

        if not lecturer_id:
            return (
                json.dumps({"success": False, "message": "Lecturer ID is required"}),
                400,
            )

        users_ref = db.collection("users")
        query = users_ref.where("lecturer_id", "==", lecturer_id).limit(1)
        docs = list(query.stream())

        if not docs:
            return (
                json.dumps(
                    {"success": False, "message": f"Lecturer {lecturer_id} not found"}
                ),
                404,
            )

        doc_ref = docs[0].reference
        doc_ref.update({"is_active": False, "status": "inactive"})

        return (
            json.dumps(
                {
                    "success": True,
                    "message": f"Lecturer {lecturer_id} has been deactivated successfully.",
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error deactivating lecturer: {e}")
        return json.dumps({"success": False, "message": "Server Error"}), 500


def get_admin_student_list():
    """
    GET handler for the Admin Student List page.
    Fetches all users with role='student' from Firestore with Active/Inactive status.
    FIX: Separated Name and Email into distinct columns to match table headers.
    """
    try:
        # Fetch all students
        students_ref = db.collection("users").where("role", "==", "student").stream()

        students = []
        for doc in students_ref:
            s = doc.to_dict()
            is_active = s.get("is_active", True)

            students.append(
                {
                    "student_id": s.get("student_id", "N/A"),
                    "name": s.get("name", "N/A"),
                    "email": s.get("email", "N/A"),
                    "major": s.get("major", "N/A"),
                    "year": s.get("year", "-"),
                    "semester": s.get("semester", "-"),
                    "ic": s.get("ic", "N/A"),
                    "is_active": is_active,
                }
            )

        # Sort by Student ID
        students.sort(key=lambda x: x["student_id"])

        rows_html = ""
        if not students:
            rows_html = '<tr><td colspan="6" class="text-center text-muted">No students found. Import accounts to get started.</td></tr>'
        else:
            for s in students:

                # Check if Active (default to True)
                is_active = s.get("is_active", True)
                if is_active:
                    row_class = ""
                    status_badge = '<span class="badge bg-success ms-2">Active</span>'
                    btn_text = "Deactivate"
                    btn_class = "btn-outline-danger"
                    btn_action = f"toggleRowStatus('{s['student_id']}', 'deactivate')"
                else:
                    row_class = "table-secondary text-muted"
                    status_badge = (
                        '<span class="badge bg-secondary ms-2">Inactive</span>'
                    )
                    btn_text = "Reactivate"
                    btn_class = "btn-success"
                    btn_action = f"toggleRowStatus('{s['student_id']}', 'reactivate')"

                rows_html += f"""
                <tr id="student-row-{s['student_id']}" class="{row_class}">
                    <td>
                        <span class="fw-bold">{html.escape(str(s['student_id']))}</span>
                        {status_badge}
                    </td>
                    <td>{html.escape(str(s['name']))}</td>
                    <td>{html.escape(str(s['email']))}</td>
                    <td>{html.escape(str(s['major']))}</td>
                    <td>Y{s['year']} S{s['semester']}</td>
                    <td>
                        <a href="/profile?user_id={s['student_id']}" class="btn btn-sm btn-outline-primary me-1">View</a>
                        <button class="btn btn-sm {btn_class}" onclick="{btn_action}">{btn_text}</button>
                    </td>
                </tr>
                """

        ctx = {"student_rows_html": rows_html, "total_count": len(students)}
        return render("admin_student_list.html", ctx), 200

    except Exception as e:
        error_html = f"""
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Error Fetching Students</h4>
                <p>{str(e)}</p>
                <a href="/admin/dashboard" class="btn btn-secondary">Back</a>
            </div>
        </div>
        """
        return error_html, 500


def get_admin_lecturer_list():
    """
    GET handler for the Admin Lecturer List page.
    Fetches all users with role='lecturer' from Firestore.
    """
    try:
        # Fetch all lecturers
        lecturers_ref = db.collection("users").where("role", "==", "lecturer").stream()

        lecturers = []
        for doc in lecturers_ref:
            l = doc.to_dict()

            # Check active status (Default to True if field is missing)
            is_active = l.get("is_active", True)

            lecturers.append(
                {
                    "lecturer_id": l.get("lecturer_id", "N/A"),
                    "name": l.get("name", "N/A"),
                    "email": l.get("email", "N/A"),
                    "faculty": l.get("faculty", "N/A"),
                    "ic": l.get("ic", "N/A"),
                    "is_active": is_active,
                }
            )

        # Sort by Lecturer ID
        lecturers.sort(key=lambda x: x["lecturer_id"])

        # Generate HTML rows
        rows_html = ""
        if not lecturers:
            rows_html = '<tr><td colspan="6" class="text-center text-muted">No lecturers found. Import accounts to get started.</td></tr>'
        else:
            for l in lecturers:

                is_active = l.get("is_active", True)

                if is_active:
                    row_class = ""
                    status_badge = '<span class="badge bg-success ms-2">Active</span>'

                    btn_text = "Deactivate"
                    btn_class = "btn-outline-danger"
                    btn_action = f"deactivateLecturer('{l['lecturer_id']}')"
                else:
                    row_class = "table-secondary text-muted"
                    status_badge = (
                        '<span class="badge bg-secondary ms-2">Inactive</span>'
                    )

                    btn_text = "Reactivate"
                    btn_class = "btn-success"
                    btn_action = f"reactivateLecturer('{l['lecturer_id']}')"

                rows_html += f"""
                <tr id="lecturer-row-{l['lecturer_id']}" class="{row_class}">
                    <td>
                        <span class="fw-bold">{html.escape(str(l['lecturer_id']))}</span>
                        {status_badge}
                    </td>
                    <td>{html.escape(str(l['name']))}</td>
                    <td>{html.escape(str(l['email']))}</td>
                    <td>{html.escape(str(l['faculty']))}</td>
                    <td>
                        <a href="/profile?user_id={l['lecturer_id']}" class="btn btn-sm btn-outline-primary me-1">View</a>
                        <button class="btn btn-sm {btn_class}" onclick="{btn_action}">{btn_text}</button>
                    </td>
                </tr>
                """

        ctx = {"lecturer_rows_html": rows_html, "total_count": len(lecturers)}
        return render("admin_lecturer_list.html", ctx), 200

    except Exception as e:
        error_html = f"""
        <div class="container mt-5">
            <div class="alert alert-danger">
                <h4>Error Fetching Lecturers</h4>
                <p>{str(e)}</p>
                <a href="/admin/exam-list" class="btn btn-secondary">Back</a>
            </div>
        </div>
        """
        return error_html, 500
