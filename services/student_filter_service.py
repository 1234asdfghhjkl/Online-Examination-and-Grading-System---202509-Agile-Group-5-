"""
Student Filter Service - DEBUG VERSION
"""

from typing import Dict, List
from datetime import datetime, timezone
from core.firebase_db import db


def save_exam_filters(exam_id: str, filters: Dict[str, List[str]]) -> None:
    """
    Save student filters for an exam
    """
    if not exam_id:
        raise ValueError("Exam ID is required")

    doc_ref = db.collection("exams").document(exam_id)

    if not doc_ref.get().exists:
        raise ValueError(f"Exam {exam_id} does not exist")

    # Clean filters - ensure all values are strings
    cleaned_filters = {
        "years": [str(y) for y in filters.get("years", []) if y],
        "majors": [str(f) for f in filters.get("majors", []) if f],
        "semesters": [str(s) for s in filters.get("semesters", []) if s],
    }

    print("📝 DEBUG save_exam_filters - Cleaning filters:")
    print(f"   Original: {filters}")
    print(f"   Cleaned: {cleaned_filters}")

    # Update Firestore
    doc_ref.update(
        {
            "student_filters": cleaned_filters,
            "filters_updated_at": datetime.now(timezone.utc),
        }
    )

    # Verify it was saved
    saved_doc = doc_ref.get()
    saved_data = saved_doc.to_dict()
    print(
        f"✅ DEBUG - Verified saved in Firestore: {saved_data.get('student_filters')}"
    )


def get_exam_filters(exam_id: str) -> Dict[str, List[str]]:
    """
    Get student filters for an exam
    """
    if not exam_id:
        return {"years": [], "majors": [], "semesters": []}

    doc_ref = db.collection("exams").document(exam_id)
    doc = doc_ref.get()

    if not doc.exists:
        print(f"⚠️ DEBUG - Exam {exam_id} not found")
        return {"years": [], "majors": [], "semesters": []}

    exam_data = doc.to_dict()
    filters = exam_data.get("student_filters", {})

    # Ensure all values are string lists
    result = {
        "years": [str(y) for y in filters.get("years", [])],
        "majors": [str(m) for m in filters.get("majors", [])],
        "semesters": [str(s) for s in filters.get("semesters", [])],
    }

    print(f"🔍 DEBUG get_exam_filters for {exam_id}:")
    print(f"   Raw from Firestore: {filters}")
    print(f"   Processed result: {result}")

    return result


def get_available_filters() -> Dict[str, List[str]]:
    """
    Get all available filter options from the student database
    """
    try:
        users_ref = db.collection("users").where("role", "==", "student").stream()

        years = set()
        majors = set()
        semesters = set()

        for doc in users_ref:
            student = doc.to_dict()

            if student.get("year") is not None:
                years.add(str(student.get("year")))

            if student.get("major"):
                majors.add(str(student.get("major")))

            if student.get("semester") is not None:
                semesters.add(str(student.get("semester")))

        result = {
            "years": sorted(list(years), key=lambda x: int(x) if x.isdigit() else 0),
            "majors": sorted(list(majors)),
            "semesters": sorted(
                list(semesters), key=lambda x: int(x) if x.isdigit() else 0
            ),
        }

        print("📊 DEBUG get_available_filters:")
        print(f"   Years: {result['years']}")
        print(f"   Majors: {result['majors']}")
        print(f"   Semesters: {result['semesters']}")

        return result

    except Exception as e:
        print(f"❌ Error fetching filter options: {e}")
        return {
            "years": ["1", "2", "3", "4"],
            "majors": [
                "Computer Science",
                "Mechanical Engineering",
                "Business Administration",
            ],
            "semesters": ["1", "2"],
        }


def get_students_by_filters(years: List[str] = None, majors: List[str] = None) -> Dict:
    """
    Get students grouped by available combinations
    """
    try:
        query = db.collection("users").where("role", "==", "student")
        students = [doc.to_dict() for doc in query.stream()]

        combinations = {}

        for student in students:
            year = str(student.get("year", ""))
            major = student.get("major", "")
            semester = str(student.get("semester", ""))

            if not year or not major:
                continue

            if years and year not in years:
                continue

            if majors and major not in majors:
                continue

            key = f"{major}|{year}"
            if key not in combinations:
                combinations[key] = {
                    "major": major,
                    "year": year,
                    "semesters": set(),
                    "count": 0,
                }

            combinations[key]["semesters"].add(semester)
            combinations[key]["count"] += 1

        result = {}
        for key, data in combinations.items():
            data["semesters"] = sorted(list(data["semesters"]))
            result[key] = data

        print("👥 DEBUG get_students_by_filters:")
        print(f"   Found {len(result)} combinations")

        return result

    except Exception as e:
        print(f"❌ Error getting student combinations: {e}")
        return {}


def is_student_eligible(student_id: str, exam_id: str) -> bool:
    """
    Check if a student is eligible to take an exam based on filters
    """
    filters = get_exam_filters(exam_id)

    # If no filters are set, exam is open to all students
    if (
        not filters.get("years")
        and not filters.get("majors")
        and not filters.get("semesters")
    ):
        return True

    student_ref = (
        db.collection("users").where("student_id", "==", student_id).limit(1).stream()
    )

    student_data = None
    for doc in student_ref:
        student_data = doc.to_dict()
        break

    if not student_data:
        return True

    student_year = str(student_data.get("year", ""))
    student_major = student_data.get("major", "")
    student_semester = str(student_data.get("semester", ""))

    # Check each filter
    if filters.get("years"):
        if student_year not in filters["years"]:
            print(
                f"❌ Student {student_id} year {student_year} not in {filters['years']}"
            )
            return False

    if filters.get("majors"):
        if student_major not in filters["majors"]:
            print(
                f"❌ Student {student_id} major {student_major} not in {filters['majors']}"
            )
            return False

    if filters.get("semesters"):
        if student_semester not in filters["semesters"]:
            print(
                f"❌ Student {student_id} semester {student_semester} not in {filters['semesters']}"
            )
            return False

    print(f"✅ Student {student_id} is eligible")
    return True


def get_filtered_students(exam_id: str) -> List[Dict]:
    """
    Get list of students who are eligible for an exam
    """
    filters = get_exam_filters(exam_id)

    query = db.collection("users").where("role", "==", "student")

    if (
        not filters.get("years")
        and not filters.get("majors")
        and not filters.get("semesters")
    ):
        return [doc.to_dict() for doc in query.stream()]

    all_students = [doc.to_dict() for doc in query.stream()]
    eligible_students = []

    for student in all_students:
        student_year = str(student.get("year", ""))
        student_major = student.get("major", "")
        student_semester = str(student.get("semester", ""))

        matches = True

        if filters.get("years"):
            if student_year not in filters["years"]:
                matches = False

        if filters.get("majors"):
            if student_major not in filters["majors"]:
                matches = False

        if filters.get("semesters"):
            if student_semester not in filters["semesters"]:
                matches = False

        if matches:
            eligible_students.append(student)

    print(f"🔍 DEBUG get_filtered_students for {exam_id}:")
    print(f"   Filters: {filters}")
    print(f"   Eligible: {len(eligible_students)} / {len(all_students)}")

    return eligible_students


def get_filter_summary(filters: Dict[str, List[str]]) -> str:
    """
    Generate a human-readable summary of filters
    """
    if (
        not filters.get("years")
        and not filters.get("majors")
        and not filters.get("semesters")
    ):
        return "All Students"

    parts = []

    if filters.get("years"):
        years_str = ", ".join(filters["years"])
        parts.append(f"Year {years_str}")

    if filters.get("majors"):
        majors_str = ", ".join(filters["majors"])
        parts.append(f"Major: {majors_str}")

    if filters.get("semesters"):
        semesters_str = ", ".join(filters["semesters"])
        parts.append(f"Semester {semesters_str}")

    return " | ".join(parts)
