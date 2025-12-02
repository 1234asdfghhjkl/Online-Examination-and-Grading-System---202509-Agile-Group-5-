from urllib.parse import parse_qs
import html
from datetime import datetime

from core.validation import validate_result_release_date
from services.exam_service import (
    get_all_published_exams_for_admin,
    get_exam_by_id,
    set_result_release_date
)
from .template_engine import render


def _parse_form(body: str) -> dict:
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    return {
        "exam_id": get_field("exam_id"),
        "release_date": get_field("release_date"),
        "release_time": get_field("release_time"),
    }


def get_admin_exam_list():
    """
    GET handler for admin exam list with result release date management
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
            
            # Get result release information
            release_date = exam.get("result_release_date", "")
            release_time = exam.get("result_release_time", "00:00")
            
            # Check if results are already released
            release_status = ""
            if release_date:
                try:
                    release_datetime_str = f"{release_date} {release_time}"
                    release_dt = datetime.strptime(release_datetime_str, "%Y-%m-%d %H:%M")
                    now = datetime.now()
                    
                    if now >= release_dt:
                        release_status = '<span class="badge bg-success ms-2">Results Released</span>'
                    else:
                        release_status = '<span class="badge bg-warning text-dark ms-2">Scheduled</span>'
                except ValueError:
                    pass
            else:
                release_status = '<span class="badge bg-secondary ms-2">Not Set</span>'
            
            release_display = f"{release_date} at {release_time}" if release_date else "Not set"

            exam_list_html += f"""
            <div class="exam-card">
                <div class="exam-info">
                    <h5 class="exam-title">
                        {title}
                        <span class="exam-status status-published">Published</span>
                        {release_status}
                    </h5>
                    <p class="exam-desc">{description}</p>
                    <div class="exam-meta">
                        <span>📅 Exam: {exam_date}</span>
                        <span>🕐 {start_time} - {end_time}</span>
                        <span>⏱️ {duration} mins</span>
                        <span class="exam-id">ID: {e_id}</span>
                    </div>
                    <div class="exam-meta mt-2">
                        <span><strong>📊 Result Release:</strong> {release_display}</span>
                    </div>
                </div>
                <div class="exam-actions">
                    <a href="/admin/set-result-release?exam_id={e_id}" 
                       class="btn btn-sm btn-primary">Set Release Date</a>
                    <a href="/grade-submissions?exam_id={e_id}" 
                       class="btn btn-sm btn-success">Grade Submissions</a>
                </div>
            </div>
            """

    html_str = render("admin_exam_list.html", {"exam_list_html": exam_list_html})
    return html_str, 200


def get_set_result_release(exam_id: str):
    """
    GET handler for setting result release date
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
    """
    form = _parse_form(body)
    exam_id = form.get("exam_id")
    
    if not exam_id:
        ctx = dict(form)
        ctx["errors_html"] = '<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam ID is missing.</div>'
        ctx["success_html"] = ""
        ctx["title"] = ""
        ctx["exam_date"] = ""
        html_str = render("set_result_release.html", ctx)
        return html_str, 400

    # Get exam to validate
    exam = get_exam_by_id(exam_id)
    if not exam:
        ctx = dict(form)
        ctx["errors_html"] = f'<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam "{exam_id}" not found.</div>'
        ctx["success_html"] = ""
        ctx["title"] = ""
        ctx["exam_date"] = ""
        html_str = render("set_result_release.html", ctx)
        return html_str, 404

    # Validation
    errors = validate_result_release_date(
        form["release_date"],
        exam.get("exam_date")
    )

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