from datetime import datetime
from typing import Optional, Dict

from core.firebase_db import db


def _generate_exam_id() -> str:
    exams = db.collection("exams").get()
    next_number = len(exams) + 1
    return f"EID-{next_number:03d}"


def save_exam_draft(
    exam_id: Optional[str],
    title: str,
    description: str,
    duration: str,
    instructions: str,
    exam_date: str,
    start_time: str = "00:00",  # CHANGED: exam_time → start_time
    end_time: str = "01:00",  # NEW: Add end_time parameter
) -> str:
    duration_int = int(duration)

    exam_data = {
        "title": title.strip(),
        "description": description.strip(),
        "duration": duration_int,
        "instructions": instructions.strip(),
        "exam_date": exam_date.strip(),
        "start_time": start_time.strip(),  # CHANGED
        "end_time": end_time.strip(),  # NEW
        "status": "draft",
        "updated_at": datetime.utcnow(),
    }

    if exam_id:
        # Update existing draft
        doc_ref = db.collection("exams").document(exam_id)
    else:
        # Create new draft with new exam_id as document ID
        exam_id = _generate_exam_id()
        doc_ref = db.collection("exams").document(exam_id)
        exam_data["exam_id"] = exam_id
        exam_data["created_at"] = datetime.utcnow()

    doc_ref.set(exam_data, merge=True)
    return exam_id


def publish_exam(exam_id: str):
    if not exam_id:
        raise ValueError("Missing exam ID.")

    doc_ref = db.collection("exams").document(exam_id)
    snap = doc_ref.get()
    if not snap.exists:
        raise ValueError(f"Exam '{exam_id}' does not exist.")

    doc_ref.update(
        {
            "status": "published",
            "published_at": datetime.utcnow(),
        }
    )


def get_exam_by_id(exam_id: str) -> Optional[Dict]:
    if not exam_id:
        return None

    # Case 1: exam_id is the document ID
    doc_ref = db.collection("exams").document(exam_id)
    snap = doc_ref.get()
    if snap.exists:
        data = snap.to_dict()
        data.setdefault("exam_id", exam_id)
        return data

    # Case 2: exam_id is stored as a field
    query = db.collection("exams").where("exam_id", "==", exam_id).limit(1).stream()

    for doc in query:
        data = doc.to_dict()
        data.setdefault("exam_id", exam_id)
        return data

    return None


def get_all_published_exams() -> list:
    """
    Fetches all exams with status 'published'
    """
    try:
        # Remove the order_by to avoid index requirement
        query = db.collection("exams").where("status", "==", "published").stream()

        exams = []
        for doc in query:
            data = doc.to_dict()
            data["exam_id"] = doc.id  # Ensure ID is included
            exams.append(data)

        # Sort in Python instead
        exams.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)

        return exams
    except Exception as e:
        print(f"Error fetching published exams: {e}")
        return []


def get_all_exams() -> list:
    """
    Fetches all exams (both draft and published)
    """
    from firebase_admin import firestore

    query = (
        db.collection("exams")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    exams = []
    for doc in query:
        data = doc.to_dict()
        data["exam_id"] = doc.id  # Ensure ID is included
        exams.append(data)

    return exams
