from datetime import datetime
from typing import Optional, Dict
import secrets
from firebase_admin import firestore

from core.firebase_db import db


def _generate_exam_id() -> str:
    """
    Generate a unique exam ID using timestamp + random string
    This prevents race conditions when multiple teachers create exams simultaneously
    """
    # Use timestamp for ordering + random string for uniqueness
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = secrets.token_hex(3)  # 6 characters
    return f"EID-{timestamp}-{random_suffix}"
    
    # Alternative approach: Use Firestore auto-generated IDs
    # doc_ref = db.collection("exams").document()
    # return doc_ref.id


def save_exam_draft(
    exam_id: Optional[str],
    title: str,
    description: str,
    duration: str,
    instructions: str,
    exam_date: str,
    start_time: str = "00:00",
    end_time: str = "01:00",
) -> str:
    duration_int = int(duration)

    exam_data = {
        "title": title.strip(),
        "description": description.strip(),
        "duration": duration_int,
        "instructions": instructions.strip(),
        "exam_date": exam_date.strip(),
        "start_time": start_time.strip(),
        "end_time": end_time.strip(),
        # REMOVED: "status": "draft" from here so it doesn't overwrite published status
        "updated_at": datetime.utcnow(),
    }

    if exam_id:
        # Update existing draft/published exam
        doc_ref = db.collection("exams").document(exam_id)
        
        # SECURITY CHECK: Verify exam exists before updating
        if not doc_ref.get().exists:
            raise ValueError(f"Exam {exam_id} does not exist")
        # Status remains unchanged on update
    else:
        # Create new draft with unique exam_id
        exam_id = _generate_exam_id()
        doc_ref = db.collection("exams").document(exam_id)
        exam_data["exam_id"] = exam_id
        exam_data["created_at"] = datetime.utcnow()
        exam_data["status"] = "draft" # <--- Status is only set here for new exams

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

    # Case 2: exam_id is stored as a field (for backward compatibility)
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
        query = db.collection("exams").where("status", "==", "published").stream()

        exams = []
        for doc in query:
            data = doc.to_dict()
            data["exam_id"] = doc.id
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

    query = (
        db.collection("exams")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    exams = []
    for doc in query:
        data = doc.to_dict()
        data["exam_id"] = doc.id
        exams.append(data)

    return exams


# Admin side get exam list and set result release date
def set_result_release_date(exam_id: str, release_date: str, release_time: str = "00:00"):
    """
    Set the result release date and time for an exam
    """
    if not exam_id:
        raise ValueError("Missing exam ID.")
    
    doc_ref = db.collection("exams").document(exam_id)
    snap = doc_ref.get()
    if not snap.exists:
        raise ValueError(f"Exam '{exam_id}' does not exist.")
    
    from datetime import datetime
    
    # Validate date format
    try:
        datetime.strptime(release_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")
    
    # Validate time format
    try:
        datetime.strptime(release_time, "%H:%M")
    except ValueError:
        raise ValueError("Invalid time format. Use HH:MM.")
    
    doc_ref.update({
        "result_release_date": release_date,
        "result_release_time": release_time,
        "result_release_updated_at": datetime.utcnow(),
    })


def get_all_published_exams_for_admin() -> list:
    """
    Fetches all published exams for admin result management
    """
    try:
        query = db.collection("exams").where("status", "==", "published").stream()

        exams = []
        for doc in query:
            data = doc.to_dict()
            data["exam_id"] = doc.id
            exams.append(data)

        # Sort by exam date
        exams.sort(key=lambda x: x.get("exam_date", ""), reverse=True)

        return exams
    except Exception as e:
        print(f"Error fetching published exams: {e}")
        return []