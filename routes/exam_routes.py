from flask import Blueprint, render_template, request, redirect, flash, session
from core.validation import validate_exam, validate_exam_date
from services.exam_service import create_exam

exam_bp = Blueprint("exam_bp", __name__)


@exam_bp.route("/create-exam", methods=["GET"])
def create_exam_form():
    if request.referrer and "/edit-exam" in request.referrer:
        exam = session.get("draft_exam")
    else:
        session.pop("draft_exam", None)
        exam = None

    return render_template("create_exam.html", exam=exam)


@exam_bp.route("/create-exam", methods=["POST"])
def create_exam_submit():
    title = request.form.get("title", "")
    description = request.form.get("description", "")
    duration = request.form.get("duration", "")
    instructions = request.form.get("instructions", "")
    exam_date = request.form.get("exam_date", "")

    # Validation
    errors = validate_exam(title, description, duration, instructions)
    errors.extend(validate_exam_date(exam_date))

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect("/create-exam")

    # Store draft in SESSION
    session["draft_exam"] = {
        "title": title,
        "description": description,
        "duration": duration,
        "instructions": instructions,
        "exam_date": exam_date,
    }

    return render_template("exam_created.html", exam=session["draft_exam"])


@exam_bp.route("/edit-exam", methods=["POST"])
def edit_exam():
    exam = {
        "title": request.form.get("title", ""),
        "description": request.form.get("description", ""),
        "duration": request.form.get("duration", ""),
        "instructions": request.form.get("instructions", ""),
        "exam_date": request.form.get("exam_date", ""),
    }

    session["draft_exam"] = exam

    return render_template("create_exam.html", exam=exam)


@exam_bp.route("/publish-exam", methods=["POST"])
def publish_exam():
    draft = session.get("draft_exam")

    if not draft:
        flash("No draft exam found.", "error")
        return redirect("/create-exam")

    # Save to Firestore
    exam_id = create_exam(
        draft["title"],
        draft["description"],
        draft["duration"],
        draft["instructions"],
        draft["exam_date"],
    )

    # Build exam dictionary including exam_id
    exam = {
        "exam_id": exam_id,
        "title": draft["title"],
        "description": draft["description"],
        "duration": int(draft["duration"]),
        "instructions": draft["instructions"],
        "exam_date": draft["exam_date"],
    }

    # Clear draft
    session.pop("draft_exam", None)

    return render_template("publish_success.html", exam=exam)
