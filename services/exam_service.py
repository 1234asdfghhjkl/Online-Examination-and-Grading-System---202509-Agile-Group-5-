from datetime import datetime
from typing import Optional, Dict, List
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
        exam_data["status"] = "draft"  # <--- Status is only set here for new exams

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
def set_result_release_date(
    exam_id: str, release_date: str, release_time: str = "00:00"
):
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

    doc_ref.update(
        {
            "result_release_date": release_date,
            "result_release_time": release_time,
            "result_release_updated_at": datetime.utcnow(),
        }
    )


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


def save_grading_settings(
    exam_id: str,
    grading_deadline_date: str,
    grading_deadline_time: str,
    release_date: str,
    release_time: str,
) -> None:
    """
    Save grading deadline and result release settings for an exam

    Args:
        exam_id: Exam identifier
        grading_deadline_date: Date when lecturers must finish grading (YYYY-MM-DD)
        grading_deadline_time: Time for grading deadline (HH:MM)
        release_date: Date when results are released to students (YYYY-MM-DD)
        release_time: Time for result release (HH:MM)

    Raises:
        ValueError: If exam not found or validation fails
    """
    if not exam_id:
        raise ValueError("Exam ID is required")

    # Check exam exists
    doc_ref = db.collection("exams").document(exam_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise ValueError(f"Exam {exam_id} not found")

    # Update the exam document
    doc_ref.update(
        {
            "grading_deadline_date": grading_deadline_date,
            "grading_deadline_time": grading_deadline_time,
            "result_release_date": release_date,
            "result_release_time": release_time,
            "settings_updated_at": datetime.utcnow(),
        }
    )


def get_all_published_exams_for_admin() -> List[Dict]:
    """
    Get all published exams with grading and release information
    Used by admin interface

    Returns:
        List of exam dictionaries with all fields
    """
    exams = []

    query = db.collection("exams").where("status", "==", "published").stream()

    for doc in query:
        exam = doc.to_dict()
        exam["exam_id"] = doc.id
        exams.append(exam)

    # Sort by exam date (most recent first)
    exams.sort(key=lambda x: x.get("exam_date", ""), reverse=True)

    return exams


def check_grading_locked(exam_id: str) -> tuple[bool, str, dict]:
    """
    Check if grading period has ended for an exam

    Args:
        exam_id: Exam identifier

    Returns:
        Tuple of (is_locked, message, details_dict)
        - is_locked: True if grading deadline has passed
        - message: Human-readable status message
        - details_dict: Additional information
    """
    exam = get_exam_by_id(exam_id)

    if not exam:
        return True, "Exam not found", {"error": "not_found"}

    deadline_date = exam.get("grading_deadline_date")
    deadline_time = exam.get("grading_deadline_time", "23:59")

    # No deadline = always open (legacy exams)
    if not deadline_date:
        return (
            False,
            "No deadline set - grading always open",
            {"has_deadline": False, "legacy_mode": True},
        )

    try:
        deadline_str = f"{deadline_date} {deadline_time}"
        deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
        now = datetime.now()

        is_locked = now > deadline_dt

        if is_locked:
            time_passed = now - deadline_dt
            days_passed = time_passed.days
            hours_passed = time_passed.seconds // 3600

            return (
                True,
                f"Locked {days_passed}d {hours_passed}h ago",
                {
                    "deadline": deadline_dt.strftime("%Y-%m-%d %H:%M"),
                    "locked_at": deadline_dt.strftime("%Y-%m-%d %H:%M"),
                    "time_passed_days": days_passed,
                    "time_passed_hours": hours_passed,
                },
            )
        else:
            time_remaining = deadline_dt - now
            days_remaining = time_remaining.days
            hours_remaining = time_remaining.seconds // 3600

            return (
                False,
                f"{days_remaining}d {hours_remaining}h remaining",
                {
                    "deadline": deadline_dt.strftime("%Y-%m-%d %H:%M"),
                    "time_remaining_days": days_remaining,
                    "time_remaining_hours": hours_remaining,
                    "urgency": "critical" if days_remaining == 0 else "normal",
                },
            )

    except ValueError as e:
        return (
            True,
            f"Invalid deadline format: {e}",
            {"error": "invalid_format", "message": str(e)},
        )


def finalize_exam_results(exam_id: str, admin_id: str = "system") -> Dict:
    """
    Finalize all results for an exam
    This locks ALL grading permanently and prepares for publication

    Args:
        exam_id: Exam identifier
        admin_id: ID of admin finalizing results

    Returns:
        Dictionary with finalization details

    Raises:
        ValueError: If exam not ready for finalization
    """
    from services.grading_service import get_student_submission

    exam = get_exam_by_id(exam_id)
    if not exam:
        raise ValueError("Exam not found")

    # Check if already finalized
    if exam.get("results_finalized"):
        raise ValueError("Results already finalized for this exam")

    # Get all submissions
    submissions_query = (
        db.collection("submissions").where("exam_id", "==", exam_id).stream()
    )

    submissions = [doc.to_dict() for doc in submissions_query]

    if not submissions:
        raise ValueError("No submissions found for this exam")

    # Check all submissions are graded
    ungraded = []
    for sub in submissions:
        student_id = sub.get("student_id")
        if not sub.get("mcq_graded"):
            ungraded.append(f"{student_id} (MCQ)")
        elif not sub.get("sa_graded"):
            ungraded.append(f"{student_id} (Short Answer)")

    if ungraded:
        raise ValueError(
            f"Cannot finalize: {len(ungraded)} submission(s) need grading. "
            f"Students: {', '.join(ungraded[:3])}"
            + (f" and {len(ungraded)-3} more" if len(ungraded) > 3 else "")
        )

    # Calculate statistics
    stats = calculate_exam_statistics(submissions)

    # Mark exam as finalized
    db.collection("exams").document(exam_id).update(
        {
            "results_finalized": True,
            "finalized_at": datetime.utcnow(),
            "finalized_by": admin_id,
            "statistics": stats,
            "grading_permanently_locked": True,
        }
    )

    return {
        "status": "success",
        "finalized_at": datetime.utcnow(),
        "total_students": stats["total_students"],
        "average_score": stats["average_percentage"],
        "pass_rate": stats["pass_rate"],
    }


def calculate_exam_statistics(submissions: List[Dict]) -> Dict:
    """
    Calculate comprehensive exam statistics

    Args:
        submissions: List of submission dictionaries

    Returns:
        Dictionary with statistics
    """
    if not submissions:
        return {
            "total_students": 0,
            "average_percentage": 0,
            "highest_score": 0,
            "lowest_score": 0,
            "pass_rate": 0,
        }

    # Extract scores
    scores = []
    for sub in submissions:
        overall_pct = sub.get("overall_percentage", 0)
        scores.append(overall_pct)

    # Calculate basic stats
    total_students = len(scores)
    average_pct = sum(scores) / total_students if total_students > 0 else 0
    highest = max(scores) if scores else 0
    lowest = min(scores) if scores else 0

    # Pass rate (assuming 50% is passing)
    passing_threshold = 50
    passed = len([s for s in scores if s >= passing_threshold])
    pass_rate = (passed / total_students * 100) if total_students > 0 else 0

    # Grade distribution
    grade_dist = calculate_grade_distribution(scores)

    return {
        "total_students": total_students,
        "average_percentage": round(average_pct, 2),
        "highest_score": round(highest, 2),
        "lowest_score": round(lowest, 2),
        "pass_rate": round(pass_rate, 2),
        "grade_distribution": grade_dist,
    }


def calculate_grade_distribution(scores: List[float]) -> Dict:
    """
    Calculate grade distribution based on score ranges

    Args:
        scores: List of percentage scores

    Returns:
        Dictionary with grade counts
    """
    distribution = {
        "A": 0,  # 80-100
        "B": 0,  # 70-79
        "C": 0,  # 60-69
        "D": 0,  # 50-59
        "F": 0,  # 0-49
    }

    for score in scores:
        if score >= 80:
            distribution["A"] += 1
        elif score >= 70:
            distribution["B"] += 1
        elif score >= 60:
            distribution["C"] += 1
        elif score >= 50:
            distribution["D"] += 1
        else:
            distribution["F"] += 1

    return distribution


def get_exam_by_id(exam_id: str) -> Optional[Dict]:
    """
    Get exam by ID
    (Include this if not already in your exam_service.py)

    Args:
        exam_id: Exam identifier

    Returns:
        Exam dictionary or None if not found
    """
    if not exam_id:
        return None

    doc_ref = db.collection("exams").document(exam_id)
    doc = doc_ref.get()

    if not doc.exists:
        return None

    exam = doc.to_dict()
    exam["exam_id"] = doc.id
    return exam


def set_result_release_date(exam_id: str, release_date: str, release_time: str) -> None:
    """
    Set result release date for an exam (legacy function)

    Args:
        exam_id: Exam identifier
        release_date: Release date (YYYY-MM-DD)
        release_time: Release time (HH:MM)

    Raises:
        ValueError: If exam not found
    """
    if not exam_id:
        raise ValueError("Exam ID is required")

    doc_ref = db.collection("exams").document(exam_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise ValueError(f"Exam {exam_id} not found")

    doc_ref.update(
        {
            "result_release_date": release_date,
            "result_release_time": release_time,
            "updated_at": datetime.utcnow(),
        }
    )
