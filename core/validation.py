from datetime import datetime

def validate_exam(title: str, description: str, duration: str, instructions: str):
    """
    Validate exam fields. Returns a list of error messages (empty if valid).
    """
    errors = []

    title = (title or "").strip()
    description = (description or "").strip()
    duration = (duration or "").strip()
    instructions = (instructions or "").strip()

    if not title:
        errors.append("Title is required.")
    if not description:
        errors.append("Description is required.")
    if not duration:
        errors.append("Duration is required.")
    elif not duration.isdigit() or int(duration) <= 0:
        errors.append("Duration must be a positive number.")
    if not instructions:
        errors.append("Instructions are required.")

    return errors


def validate_exam_date(exam_date: str):
    errors = []

    if not exam_date:
        errors.append("Exam date is required.")
        return errors

    try:
        selected_date = datetime.strptime(exam_date, "%Y-%m-%d").date()
        today = datetime.today().date()
        if selected_date < today:
            errors.append("Exam date cannot be in the past.")
    except ValueError:
        errors.append("Invalid exam date format.")

    return errors
