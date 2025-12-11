from urllib.parse import parse_qs
import html
import json
from core.validation import validate_exam, validate_exam_date, validate_exam_times
from services.exam_service import (
    save_exam_draft,
    publish_exam,
    get_exam_by_id,
    check_grading_locked,
    soft_delete_exam,
    delete_exam_and_contents,
    get_exams_by_lecturer,
    get_all_exams,
)
from services.question_service import has_mcq_for_exam, has_short_for_exam
from services.student_filter_service import (
    save_exam_filters,
    get_exam_filters,
    get_filter_summary,
)
from .template_engine import render


def _parse_form(body: str) -> dict:
    data = parse_qs(body)

    def get_field(key: str) -> str:
        return data.get(key, [""])[0]

    def get_multi(key: str) -> list:
        return data.get(key, [])

    return {
        "exam_id": get_field("exam_id"),
        "title": get_field("title"),
        "description": get_field("description"),
        "duration": get_field("duration"),
        "exam_date": get_field("exam_date"),
        "start_time": get_field("start_time"),
        "end_time": get_field("end_time"),
        "instructions": get_field("instructions"),
        "filter_years": get_multi("filter_year"),
        "filter_majors": get_multi("filter_major"),
        "filter_semesters": get_multi("filter_semester"),
        "lecturer_id": get_field("lecturer_id"),
    }


def _build_filter_context(filters: dict, available_majors: list = None) -> dict:
    """Build context for filter checkboxes"""
    years = filters.get("years", [])
    majors = filters.get("majors", [])
    semesters = filters.get("semesters", [])

    if not available_majors:
        available_majors = [
            "Computer Science",
            "Mechanical Engineering",
            "Business Administration",
        ]

    context = {
        "year1_checked": "checked" if "1" in years else "",
        "year2_checked": "checked" if "2" in years else "",
        "year3_checked": "checked" if "3" in years else "",
        "year4_checked": "checked" if "4" in years else "",
        "sem1_checked": "checked" if "1" in semesters else "",
        "sem2_checked": "checked" if "2" in semesters else "",
        "available_majors": available_majors,
    }

    for major in available_majors:
        safe_key = major.replace(" ", "_").lower()
        context[f"major_{safe_key}_checked"] = "checked" if major in majors else ""
        context[f"major_{safe_key}_name"] = major

    return context


# ---------- GET handlers ----------


def get_create_exam(lecturer_id: str = ""):
    html_str = render(
        "create_exam.html",
        {
            "lecturer_id": lecturer_id,
            "exam_id": "",
            "title": "",
            "description": "",
            "duration": "",
            "exam_date": "",
            "start_time": "",
            "end_time": "",
            "instructions": "",
            "errors_html": "",
            **_build_filter_context({}),
        },
    )
    return html_str, 200


def get_edit_exam(exam_id: str):
    if not exam_id:
        html_str = render(
            "exam_edit.html",
            {
                "errors_html": '<div class="alert alert-danger">Error: Exam ID is missing.</div>',
                "filters_json": "{}",
            },
        )
        return html_str, 400

    exam = get_exam_by_id(exam_id)

    if not exam:
        html_str = render(
            "exam_edit.html",
            {
                "errors_html": f'<div class="alert alert-danger">Error: Exam ID "{exam_id}" not found.</div>',
                "filters_json": "{}",
            },
        )
        return html_str, 404

    # ✅ FIX: Get existing filters
    filters = get_exam_filters(exam_id)

    print(f"🔍 DEBUG - Retrieved filters for {exam_id}: {filters}")  # Debug

    # Create clean JSON
    filters_json_str = json.dumps(filters)

    from services.student_filter_service import get_available_filters

    available = get_available_filters()

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": str(exam.get("duration", "")),
        "exam_date": exam.get("exam_date", ""),
        "success_html": "",
        "errors_html": "",
        "start_time": exam.get("start_time", "00:00"),
        "end_time": exam.get("end_time", "01:00"),
        "instructions": exam.get("instructions", ""),
        "filters_json": filters_json_str,
        **_build_filter_context(filters, available.get("majors", [])),
    }

    html_str = render("exam_edit.html", ctx)
    return html_str, 200


# ---------- POST handlers ----------


def post_edit_exam(body: str):
    form = _parse_form(body)
    exam_id = form.get("exam_id")

    if not exam_id:
        ctx = dict(form)
        ctx["errors_html"] = (
            '<div class="alert alert-danger mb-3"><strong>Error:</strong> Exam ID is missing.</div>'
        )
        html_str = render("exam_edit.html", ctx)
        return html_str, 400

    # 1. Validation
    errors = validate_exam(
        form["title"], form["description"], form["duration"], form["instructions"]
    )
    errors.extend(validate_exam_date(form["exam_date"]))
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

        filters = {
            "years": form.get("filter_years", []),
            "majors": form.get("filter_majors", []),
            "semesters": form.get("filter_semesters", []),
        }

        from services.student_filter_service import get_available_filters

        available = get_available_filters()

        ctx = dict(form)
        ctx["start_time"] = form["start_time"]
        ctx["end_time"] = form["end_time"]
        ctx["errors_html"] = errors_html
        ctx["success_html"] = ""
        ctx["filters_json"] = json.dumps(filters)
        ctx.update(_build_filter_context(filters, available.get("majors", [])))

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
            start_time=form["start_time"],
            end_time=form["end_time"],
        )

        # ✅ FIX: Save filters separately
        filters = {
            "years": form.get("filter_years", []),
            "majors": form.get("filter_majors", []),
            "semesters": form.get("filter_semesters", []),
        }

        print(f"💾 DEBUG - Saving filters for {exam_id}: {filters}")  # Debug

        save_exam_filters(exam_id, filters)

        # Verify save worked
        saved_filters = get_exam_filters(exam_id)
        print(f"✅ DEBUG - Verified saved filters: {saved_filters}")  # Debug

        # 4. Success
        success_html = """
        <div class="alert alert-success mb-3">
            <strong>Success!</strong> Exam details and filters saved.
        </div>
        """

        from services.student_filter_service import get_available_filters

        available = get_available_filters()

        ctx = dict(form)
        ctx["success_html"] = success_html
        ctx["errors_html"] = ""
        ctx["filters_json"] = json.dumps(filters)
        ctx.update(_build_filter_context(filters, available.get("majors", [])))

        html_str = render("exam_edit.html", ctx)
        return html_str, 200

    except ValueError as e:
        errors_html = f"""
        <div class="alert alert-danger mb-3">
            <strong>Database Error:</strong> {html.escape(str(e))}
        </div>
        """

        filters = {
            "years": form.get("filter_years", []),
            "majors": form.get("filter_majors", []),
            "semesters": form.get("filter_semesters", []),
        }

        ctx = dict(form)
        ctx["errors_html"] = errors_html
        ctx["filters_json"] = json.dumps(filters)
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

    # Save basic exam details (this will NOT overwrite filters because we use merge=True)
    # Note: save_exam_draft here updates status if it was draft, or just content
    exam_id = save_exam_draft(
        exam_id=form["exam_id"],
        title=form["title"],
        description=form["description"],
        duration=form["duration"],
        instructions=form["instructions"],
        exam_date=form["exam_date"],
        start_time=form["start_time"],
        end_time=form["end_time"],
    )

    # Change status to published
    publish_exam(exam_id)

    # Get the saved filters for display
    filters = get_exam_filters(exam_id)

    # FIX: Fetch the exam again to get the owner (created_by)
    # This guarantees we have the correct ID for the success page button
    exam = get_exam_by_id(exam_id)
    lecturer_id = exam.get("created_by", "") if exam else form.get("lecturer_id", "")

    ctx = dict(form)
    ctx["exam_id"] = exam_id
    ctx["filter_summary"] = get_filter_summary(filters)
    ctx["lecturer_id"] = lecturer_id  # <--- Pass to template

    html_str = render("exam_published.html", ctx)
    return html_str, 200


def post_submit_exam(body: str):
    form = _parse_form(body)

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

        filters = {
            "years": form.get("filter_years", []),
            "majors": form.get("filter_majors", []),
            "semesters": form.get("filter_semesters", []),
        }

        from services.student_filter_service import get_available_filters

        available = get_available_filters()

        ctx = dict(form)
        ctx["errors_html"] = errors_html
        ctx.update(_build_filter_context(filters, available.get("majors", [])))

        html_str = render("create_exam.html", ctx)
        return html_str, 400

    # Valid: Save/update draft in DB
    exam_id = save_exam_draft(
        exam_id=form["exam_id"] or None,
        title=form["title"],
        description=form["description"],
        duration=form["duration"],
        instructions=form["instructions"],
        exam_date=form["exam_date"],
        start_time=form["start_time"],
        end_time=form["end_time"],
        created_by=form.get("lecturer_id"),  # <--- THIS IS THE KEY FIX
    )

    # Save filters
    filters = {
        "years": form.get("filter_years", []),
        "majors": form.get("filter_majors", []),
        "semesters": form.get("filter_semesters", []),
    }

    save_exam_filters(exam_id, filters)

    has_mcq = has_mcq_for_exam(exam_id)
    has_short = has_short_for_exam(exam_id)

    ctx = dict(form)
    ctx["exam_id"] = exam_id
    ctx["filter_summary"] = get_filter_summary(filters)

    if has_mcq:
        ctx["mcq_button_label"] = "View / Edit MCQ"
        ctx["mcq_button_class"] = "btn btn-primary"
    else:
        ctx["mcq_button_label"] = "Build MCQ"
        ctx["mcq_button_class"] = "btn btn-outline-primary"

    if has_short:
        ctx["short_button_label"] = "View / Edit Short Answers"
        ctx["short_button_class"] = "btn btn-primary"
    else:
        ctx["short_button_label"] = "Build Short Answers"
        ctx["short_button_class"] = "btn btn-outline-primary"

    html_str = render("exam_review.html", ctx)
    return html_str, 200


# --- Additional handlers (keeping existing code) ---


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
                "filter_summary": "All Students",
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
                "filter_summary": "All Students",
            },
        )
        return html_str, 404

    start_time = exam.get("start_time", "")
    end_time = exam.get("end_time", "")
    duration = exam.get("duration", 0)

    if not start_time and exam.get("exam_time"):
        start_time = exam.get("exam_time", "00:00")
        if duration:
            start_h, start_m = map(int, start_time.split(":"))
            total_minutes = start_h * 60 + start_m + int(duration)
            end_h = (total_minutes // 60) % 24
            end_m = total_minutes % 60
            end_time = f"{end_h:02d}:{end_m:02d}"

    if not start_time:
        start_time = "00:00"
    if not end_time:
        end_time = "01:00"

    filters = get_exam_filters(exam_id)
    filter_summary = get_filter_summary(filters)

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": str(duration),
        "exam_date": exam.get("exam_date", ""),
        "start_time": start_time,
        "end_time": end_time,
        "instructions": exam.get("instructions", ""),
        "filter_summary": filter_summary,
        # FIX: Ensure we recover the lecturer ID from the database
        "lecturer_id": exam.get("created_by", ""),
    }

    has_mcq = has_mcq_for_exam(ctx["exam_id"])
    has_short = has_short_for_exam(ctx["exam_id"])

    if has_mcq:
        ctx["mcq_button_label"] = "View / Edit MCQ"
        ctx["mcq_button_class"] = "btn btn-primary"
    else:
        ctx["mcq_button_label"] = "Build MCQ"
        ctx["mcq_button_class"] = "btn btn-outline-primary"

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
                "filter_summary": "All Students",
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
                "filter_summary": "All Students",
            },
        )
        return html_str, 404

    start_time = exam.get("start_time", "")
    end_time = exam.get("end_time", "")
    duration = exam.get("duration", 0)

    if not start_time and exam.get("exam_time"):
        start_time = exam.get("exam_time", "00:00")
        if duration:
            start_h, start_m = map(int, start_time.split(":"))
            total_minutes = start_h * 60 + start_m + int(duration)
            end_h = (total_minutes // 60) % 24
            end_m = total_minutes % 60
            end_time = f"{end_h:02d}:{end_m:02d}"

    if not start_time:
        start_time = "00:00"
    if not end_time:
        end_time = "01:00"

    filters = get_exam_filters(exam_id)
    filter_summary = get_filter_summary(filters)

    ctx = {
        "exam_id": exam.get("exam_id", exam_id),
        "title": exam.get("title", ""),
        "description": exam.get("description", ""),
        "duration": str(duration),
        "exam_date": exam.get("exam_date", ""),
        "start_time": start_time,
        "end_time": end_time,
        "instructions": exam.get("instructions", ""),
        "filter_summary": filter_summary,
        # FIX: Ensure we recover the lecturer ID from the database
        "lecturer_id": exam.get("created_by", ""),
    }

    html_str = render("exam_published.html", ctx)
    return html_str, 200


def get_exam_delete(exam_id: str, method: str = "hard"):
    """Delete exam flow"""
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


def get_exam_list(
    success_message: str = "",
    search: str = "",
    sort: str = "date",
    lecturer_id: str = None,
):
    """GET handler for listing exams, optionally filtered by lecturer"""

    if lecturer_id:
        # Filter: Only exams created by this lecturer
        all_exams = get_exams_by_lecturer(lecturer_id)
    else:
        # No ID provided: Show all (Admin behavior or legacy)
        all_exams = get_all_exams()

    if search:
        term = search.lower()
        all_exams = [
            exam for exam in all_exams if term in str(exam.get("title", "")).lower()
        ]

    if sort == "title":
        all_exams.sort(key=lambda e: str(e.get("title", "")).lower())
    else:
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

            start_time = exam.get("start_time", "")
            end_time = exam.get("end_time", "")

            if not start_time and exam.get("exam_time"):
                start_time = exam.get("exam_time", "N/A")
                if duration and start_time != "N/A":
                    try:
                        start_h, start_m = map(int, start_time.split(":"))
                        total_minutes = start_h * 60 + start_m + int(duration)
                        end_h = (total_minutes // 60) % 24
                        end_m = total_minutes % 60
                        end_time = f"{end_h:02d}:{end_m:02d}"
                    except Exception:
                        end_time = "N/A"

            if not start_time:
                start_time = "N/A"
            if not end_time:
                end_time = "N/A"

            status = exam.get("status", "draft")

            # Get filter summary
            filters = get_exam_filters(e_id)
            has_filters = bool(
                filters.get("years")
                or filters.get("majors")
                or filters.get("semesters")
            )

            if has_filters:
                filter_summary = get_filter_summary(filters)
                if len(filter_summary) > 50:
                    filter_summary = filter_summary[:47] + "..."
                filter_badge = f'<span class="badge bg-info text-dark ms-2" title="{html.escape(get_filter_summary(filters))}">👥 {html.escape(filter_summary)}</span>'
            else:
                filter_badge = ""

            if status == "published":
                status_badge = (
                    '<span class="exam-status status-published">Published</span>'
                )

                is_locked, lock_msg, _ = check_grading_locked(e_id)

                if is_locked:
                    grade_btn = f"""
                    <button class="btn btn-sm btn-secondary" disabled title="{html.escape(lock_msg)}">
                        🔒 Grading Closed
                    </button>
                    """
                else:
                    grade_btn = f'<a href="/grade-submissions?exam_id={e_id}" class="btn btn-sm btn-success">Grade</a>'

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
                            {title_display} {status_badge} {filter_badge}
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
            "lecturer_id": lecturer_id if lecturer_id else "",
        },
    )
    return html_str, 200
