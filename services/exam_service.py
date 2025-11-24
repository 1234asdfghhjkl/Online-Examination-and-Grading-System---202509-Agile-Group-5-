from core.firebase_db import db


def _generate_exam_id():
    exams = db.collection("exams").get()
    next_number = len(exams) + 1
    return f"EID-{next_number:03d}"  # EID-001


def create_exam(title, description, duration, instructions, exam_date):
    exam_id = _generate_exam_id()

    exam_data = {
        "exam_id": exam_id,
        "title": title.strip(),
        "description": description.strip(),
        "duration": int(duration),
        "instructions": instructions.strip(),
        "exam_date": exam_date.strip(),
    }

    db.collection("exams").document(exam_id).set(exam_data)
    return exam_id
