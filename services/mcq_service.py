from typing import Dict, List
from datetime import datetime

from core.firebase_db import db


def exam_exists(exam_id: str) -> bool:
    if not exam_id:
        return False

    # Case 1 : exam_id is the document ID
    doc = db.collection("exams").document(exam_id).get()
    if doc.exists:
        return True

    # Case 2 : exam_id is stored as a field
    query = db.collection("exams").where("exam_id", "==", exam_id).limit(1).stream()
    for _ in query:
        return True

    return False


def create_mcq_question(
    exam_id: str,
    question_text: str,
    options: Dict[str, str],
    correct_option: str,
    marks: int,
) -> str:
    if not exam_exists(exam_id):
        raise ValueError("Exam does not exist.")

    query = (
        db.collection("questions")
        .where("exam_id", "==", exam_id)
        .where("question_type", "==", "MCQ")
    )

    max_no = 0
    for doc in query.stream():
        data = doc.to_dict() or {}
        try:
            no = int(data.get("question_no", 0))
        except (TypeError, ValueError):
            no = 0
        if no > max_no:
            max_no = no

    next_no = max_no + 1

    question_doc_id = f"{exam_id}-Q{next_no}"

    doc_ref = db.collection("questions").document(question_doc_id)
    doc_data = {
        "exam_id": exam_id,
        "question_type": "MCQ",
        "question_no": next_no,
        "question_text": question_text.strip(),
        "options": {
            "A": options.get("A", "").strip(),
            "B": options.get("B", "").strip(),
            "C": options.get("C", "").strip(),
            "D": options.get("D", "").strip(),
        },
        "correct_option": correct_option,
        "marks": int(marks),
        "created_at": datetime.utcnow(),
    }
    doc_ref.set(doc_data)
    return question_doc_id


def get_mcq_questions_by_exam(exam_id: str) -> List[Dict]:
    query = (
        db.collection("questions")
        .where("exam_id", "==", exam_id)
        .where("question_type", "==", "MCQ")
    )

    questions: List[Dict] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        questions.append(data)

    # Sort ques no
    questions.sort(key=lambda q: int(q.get("question_no", 0)))

    return questions


def delete_mcq_question(question_id: str) -> None:
    if not question_id:
        return

    ref = db.collection("questions").document(question_id)
    snap = ref.get()
    if not snap.exists:
        return

    data = snap.to_dict() or {}
    exam_id = data.get("exam_id")
    if not exam_id:
        ref.delete()
        return

    ref.delete()

    questions = get_mcq_questions_by_exam(exam_id)
    new_index = 1
    for q in questions:
        old_id = q.get("id")
        if not old_id:
            continue

        q_data = q.copy()
        q_data.pop("id", None)
        q_data["question_no"] = new_index

        new_doc_id = f"{exam_id}-Q{new_index}"

        if old_id == new_doc_id:
            db.collection("questions").document(old_id).update(
                {"question_no": new_index}
            )
        else:
            dest_ref = db.collection("questions").document(new_doc_id)
            dest_ref.set(q_data)
            db.collection("questions").document(old_id).delete()

        new_index += 1


def has_mcq_for_exam(exam_id: str) -> bool:
    if not exam_id:
        return False

    query = (
        db.collection("questions")
        .where("exam_id", "==", exam_id)
        .where("question_type", "==", "MCQ")
        .limit(1)
        .stream()
    )

    for _ in query:
        return True
    return False
