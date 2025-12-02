"""
Student Submission Service
Handles retrieval of student submissions and result status
"""

from typing import List, Dict
from datetime import datetime

from core.firebase_db import db
from services.exam_service import get_exam_by_id
from services.student_result_service import check_results_released


def get_student_submissions(student_id: str) -> List[Dict]:
    """
    Get all submissions for a specific student with exam details and result status
    
    Args:
        student_id: The student's ID
        
    Returns:
        List of submission dictionaries with exam details and result status
    """
    if not student_id:
        return []
    
    # Query all submissions for this student
    query = db.collection("submissions").where("student_id", "==", student_id).stream()
    
    submissions = []
    for doc in query:
        data = doc.to_dict()
        data["submission_id"] = doc.id
        
        # Get exam details
        exam_id = data.get("exam_id")
        exam = get_exam_by_id(exam_id)
        
        if exam:
            data["exam_title"] = exam.get("title", "Unknown Exam")
            data["exam_date"] = exam.get("exam_date", "N/A")
            
            # Check if results are released
            is_released, release_date, release_time = check_results_released(exam_id)
            data["results_released"] = is_released
            data["release_date"] = release_date
            data["release_time"] = release_time
            
            # Get scores if available
            data["mcq_score"] = data.get("mcq_score", 0)
            data["mcq_total"] = data.get("mcq_total", 0)
            data["overall_percentage"] = data.get("overall_percentage", 0)
            
            submissions.append(data)
    
    # Sort by submission date (most recent first)
    submissions.sort(key=lambda x: x.get("submitted_at", datetime.min), reverse=True)
    
    return submissions