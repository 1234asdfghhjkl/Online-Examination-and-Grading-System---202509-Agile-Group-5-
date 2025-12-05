from urllib.parse import parse_qs
import html

from core.validation import validate_exam, validate_exam_date, validate_exam_times
from services.exam_service import (
    save_exam_draft,
    publish_exam,
    get_exam_by_id,
    check_grading_locked,
    soft_delete_exam,
    delete_exam_and_contents,
)
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
        "start_time": get_field("start_time"),  # CHANGED
        "end_time": get_field("end_time"),  # NEW
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
            "start_time": "",  # CHANGED
            "end_time": "",  # NEW
            "instructions": "",
            "errors_html": "",
        },
    )
    return html_str, 200


def get_edit_exam(exam_id: str):
    if not exam_id:
        # Redirect to exam list or show error if no ID is provided
        # For simplicity, we'll return an error page template
        html_str = render(
            "exam_edit.html",
            {
                "errors_html": '<div class="alert alert-danger">Error: Exam ID is missing.</div>'
            },
        )
        return html_str, 400

    exam = get_exam_by_id(exam_id)

    if not exam:
        html_str = render(
            "exam_edit.html",
            {
                "errors_html": f'<div class="alert alert-danger">Error: Exam ID "{exam_id}" not found.</div>'
            },
        )
        return html_str, 404

    # Build context from exam data
    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": str(exam.get("duration", "")),
        "exam_date": exam.get("exam_date", ""),
        # Success and error messages are empty on initial load
        "success_html": "",
        "errors_html": "",
        # start_time and end_time are not used in exam_edit.html, but keep them for safety if other components use the context.
        "start_time": exam.get("start_time", "00:00"),
        "end_time": exam.get("end_time", "01:00"),
        "instructions": exam.get("instructions", ""),
    }

    html_str = render("exam_edit.html", ctx)
    return html_str, 200


# ---------- POST handlers ----------


def post_edit_exam(body: str):
    form = _parse_form(body)
    exam_id = form.get("exam_id")

    if not exam_id:
        # Check if exam_id is provided
        ctx = dict(form)
        ctx["errors_html"] = (
            '<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam ID is missing.</div>'
        )
        html_str = render("exam_edit.html", ctx)
        return html_str, 400

    # 1. Validation (now includes time validation)
    errors = validate_exam(
        form["title"], form["description"], form["duration"], form["instructions"]
    )
    errors.extend(validate_exam_date(form["exam_date"]))
    # NEW: Validate times, as they are now submitted by the form
    errors.extend(
        validate_exam_times(form["start_time"], form["end_time"], form["duration"])
    )

    # 2. Handle errors
    if errors:
        error_items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Please fix the following:</strong>
            <ul class="mb-0">{error_items}</ul>
        </div>
        """
        ctx = dict(form)
        # We need to ensure the times are in the context for rendering the error page
        ctx["start_time"] = form["start_time"]
        ctx["end_time"] = form["end_time"]
        ctx["errors_html"] = errors_html

        # --- FIX: Ensure success_html is present in the context on failure ---
        ctx["success_html"] = ""

        html_str = render("exam_edit.html", ctx)
        return html_str, 400

    # 3. Valid: Save/update draft in DB
    try:
        save_exam_draft(
            exam_id=exam_id,
            title=form["title"],
            description=form["description"],
            duration=form["duration"],
            instructions=form["instructions"],
            exam_date=form["exam_date"],
            start_time=form["start_time"],  # <-- Use submitted time
            end_time=form["end_time"],  # <-- Use submitted time
        )

        # 4. Success
        success_html = """
        <div class="alert alert-success mb-3">
            <strong>Success!</strong> Exam details saved.
        </div>
        """
        ctx = dict(form)
        ctx["success_html"] = success_html
        ctx["errors_html"] = ""  # Clear errors on success
        html_str = render("exam_edit.html", ctx)
        return html_str, 200

    except ValueError as e:
        # Handle cases where save_exam_draft might raise an exception
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Database Error:</strong> {html.escape(str(e))}
        </div>
        """
        ctx = dict(form)
        ctx["errors_html"] = errors_html
        html_str = render("exam_edit.html", ctx)
        return html_str, 500


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
        start_time=form["start_time"],  # ← ADD THIS LINE
        end_time=form["end_time"],
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
                "exam_date": "",
                "start_time": "",
                "end_time": "",
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
                "start_time": "",
                "end_time": "",
                "instructions": "",
                "mcq_button_label": "Build MCQ",
                "mcq_button_class": "btn btn-outline-primary",
                "short_button_label": "Build Short Answers",
                "short_button_class": "btn btn-outline-primary",
            },
        )
        return html_str, 404

    # MIGRATION LOGIC: Handle old exam_time field
    start_time = exam.get("start_time", "")
    end_time = exam.get("end_time", "")
    duration = exam.get("duration", 0)

    # If start_time doesn't exist but exam_time does (old format)
    if not start_time and exam.get("exam_time"):
        start_time = exam.get("exam_time", "00:00")
        # Calculate end_time from start_time + duration
        if duration:
            start_h, start_m = map(int, start_time.split(":"))
            total_minutes = start_h * 60 + start_m + int(duration)
            end_h = (total_minutes // 60) % 24
            end_m = total_minutes % 60
            end_time = f"{end_h:02d}:{end_m:02d}"

    # Fallback defaults if still empty
    if not start_time:
        start_time = "00:00"
    if not end_time:
        end_time = "01:00"

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": str(duration),
        "exam_date": exam.get("exam_date", ""),
        "start_time": start_time,
        "end_time": end_time,
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
                "start_time": "",
                "end_time": "",
                "instructions": "",
            },
        )
        return html_str, 400

    exam = get_exam_by_id(exam_id)
    if not exam:
        html_str = render(
            "exam_published.html",
            {
                "exam_id": exam_id,
                "title": f"Exam {exam_id} not found",
                "description": "",
                "duration": "",
                "exam_date": "",
                "start_time": "",
                "end_time": "",
                "instructions": "",
            },
        )
        return html_str, 404

    # MIGRATION LOGIC: Handle old exam_time field
    start_time = exam.get("start_time", "")
    end_time = exam.get("end_time", "")
    duration = exam.get("duration", 0)

    # If start_time doesn't exist but exam_time does (old format)
    if not start_time and exam.get("exam_time"):
        start_time = exam.get("exam_time", "00:00")
        # Calculate end_time from start_time + duration
        if duration:
            start_h, start_m = map(int, start_time.split(":"))
            total_minutes = start_h * 60 + start_m + int(duration)
            end_h = (total_minutes // 60) % 24
            end_m = total_minutes % 60
            end_time = f"{end_h:02d}:{end_m:02d}"

    # Fallback defaults
    if not start_time:
        start_time = "00:00"
    if not end_time:
        end_time = "01:00"

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": str(duration),
        "exam_date": exam.get("exam_date", ""),
        "start_time": start_time,
        "end_time": end_time,
        "instructions": exam.get("instructions", ""),
    }

    html_str = render("exam_published.html", ctx)
    return html_str, 200


def get_exam_delete(exam_id: str, method: str = "hard"):
    """
    Delete exam flow:
    - method='soft'  -> mark as deleted (keep data)
    - method='hard'  -> remove exam and all related content
    """
    if not exam_id:
        html_str = """
        <div class="alert alert-danger mt-3">
            <strong>Error:</strong> Missing exam ID.
        </div>
        <a href="/exam-list" class="btn btn-primary mt-2">Back to exams</a>
        """
        return html_str, 400

    try:
        if method == "soft":
            soft_delete_exam(exam_id)
            msg = "Exam removed from list."
        else:
            delete_exam_and_contents(exam_id)
            msg = "Exam deleted successfully."
    except ValueError as e:
        html_str = f"""
        <div class="alert alert-danger mt-3">
            <strong>Could not delete exam:</strong> {html.escape(str(e))}
        </div>
        <a href="/exam-list" class="btn btn-primary mt-2">Back to exams</a>
        """
        return html_str, 404

    return get_exam_list(success_message=msg)


def get_exam_list(success_message: str = "", search: str = "", sort: str = "date"):
    """
    GET handler for listing all exams (admin view) - UPDATED FOR TIDY UI & DEADLINE LOCK
    """
    from services.exam_service import get_all_exams

    all_exams = get_all_exams()

    # ----- FILTER: search by exam title -----
    if search:
        term = search.lower()
        all_exams = [
            exam for exam in all_exams if term in str(exam.get("title", "")).lower()
        ]

    # ----- SORT: by date or title -----
    # date uses exam_date "YYYY-MM-DD" (fallback empty string)
    if sort == "title":
        all_exams.sort(key=lambda e: str(e.get("title", "")).lower())
    else:  # default = sort by date (newest first)
        all_exams.sort(
            key=lambda e: str(e.get("exam_date", "")),
            reverse=True,
        )

    exam_list_html = ""

    if not all_exams:
        exam_list_html = """
        <div class="alert alert-info">
            <h5>No exams found</h5>
            <p class="mb-0">Click "Create New Exam" to get started.</p>
        </div>
        """
    else:
        for exam in all_exams:
            if exam.get("is_deleted"):
                continue
            e_id = exam.get("exam_id", "")
            title = html.escape(exam.get("title", "Untitled"))
            description = html.escape(exam.get("description", "No description"))
            duration = exam.get("duration", 0)
            date = exam.get("exam_date", "N/A")

            # MIGRATION LOGIC: Handle old exam_time field
            start_time = exam.get("start_time", "")
            end_time = exam.get("end_time", "")

            # If start_time doesn't exist but exam_time does (old format)
            if not start_time and exam.get("exam_time"):
                start_time = exam.get("exam_time", "N/A")
                # Calculate end_time from start_time + duration
                if duration and start_time != "N/A":
                    try:
                        start_h, start_m = map(int, start_time.split(":"))
                        total_minutes = start_h * 60 + start_m + int(duration)
                        end_h = (total_minutes // 60) % 24
                        end_m = total_minutes % 60
                        end_time = f"{end_h:02d}:{end_m:02d}"
                    except Exception:
                        end_time = "N/A"

            # Fallback
            if not start_time:
                start_time = "N/A"
            if not end_time:
                end_time = "N/A"

            status = exam.get("status", "draft")

            # --- TIDY UI LOGIC ---
            if status == "published":
                status_badge = (
                    '<span class="exam-status status-published">Published</span>'
                )

                # --- CHECK GRADING DEADLINE ---
                is_locked, lock_msg, _ = check_grading_locked(e_id)

                if is_locked:
                    # If locked, show disabled gray button
                    grade_btn = f"""
                    <button class="btn btn-sm btn-secondary" disabled title="{html.escape(lock_msg)}">
                        🔒 Grading Closed
                    </button>
                    """
                else:
                    # If open, show normal green button
                    grade_btn = f'<a href="/grade-submissions?exam_id={e_id}" class="btn btn-sm btn-success">Grade</a>'

                # UPDATED ACTIONS:
                # 1. Removed "Student Test" button
                # 2. Updated "Grade" button logic
                actions = f"""
                    <a href="/exam-edit?exam_id={e_id}" class="btn btn-sm btn-outline-primary">Edit Details</a>
                    <a href="/exam-review?exam_id={e_id}" class="btn btn-sm btn-info">View</a>
                    {grade_btn}
                    <button type="button"
                        class="btn btn-sm btn-danger"
                        data-bs-toggle="modal"
                        data-bs-target="#deleteExamModal"
                        data-exam-id="{e_id}"
                        data-exam-title="{title}">
                        Delete
                    </button>

                """
            else:
                status_badge = '<span class="exam-status status-draft">Draft</span>'
                actions = f"""
                    <a href="/exam-edit?exam_id={e_id}" class="btn btn-sm btn-outline-primary">Edit Details</a>
                    <a href="/exam-review?exam_id={e_id}" class="btn btn-sm btn-primary">Add Questions / Review</a>
                    <button type="button"
                        class="btn btn-sm btn-danger"
                        data-bs-toggle="modal"
                        data-bs-target="#deleteExamModal"
                        data-exam-id="{e_id}"
                        data-exam-title="{title}">
                        Delete
                    </button>
                """

            title_raw = exam.get("title", "Untitled")
            title_display = html.escape(title_raw)
            title_key = html.escape(title_raw.lower())
            date = exam.get("exam_date", "N/A")

            exam_list_html += f"""
                <div class="exam-card" data-title="{title_key}" data-date="{date}">
                    <div class="exam-info">
                        <h5 class="exam-title">
                            {title_display} {status_badge}
                        </h5>
                        <p class="exam-desc">{description}</p>
                        <div class="exam-meta">
                            <span>📅 {date}</span>
                            <span>🕐 {start_time} - {end_time}</span>
                            <span>⏱️ {duration} mins</span>
                            <span class="exam-id">ID: {e_id}</span>
                        </div>
                    </div>
                    <div class="exam-actions">
                        {actions}
                    </div>
                </div>
            """

    html_str = render(
        "exam_list.html",
        {
            "exam_list_html": exam_list_html,
            "success_message": success_message,
            "search": search,
            "sort": sort,
        },
    )
    return html_str, 200


def post_submit_exam(body: str):
    form = _parse_form(body)

    # DEBUG
    print("=" * 60)
    print("DEBUG post_submit_exam - Form received:")
    print(f"  start_time: '{form.get('start_time')}'")
    print(f"  end_time: '{form.get('end_time')}'")
    print(f"  duration: '{form.get('duration')}'")
    print("=" * 60)

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
        start_time=form["start_time"],
        end_time=form["end_time"],
    )

    # DEBUG
    print(f"DEBUG: Saved exam {exam_id} to database")
    print(f"  with start_time: {form['start_time']}, end_time: {form['end_time']}")

    has_mcq = has_mcq_for_exam(exam_id)
    has_short = has_short_for_exam(exam_id)

    ctx = dict(form)
    ctx["exam_id"] = exam_id

    # DEBUG
    print("DEBUG: Context for exam_review.html:")
    print(f"  start_time: '{ctx.get('start_time')}'")
    print(f"  end_time: '{ctx.get('end_time')}'")
    print("=" * 60)

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
