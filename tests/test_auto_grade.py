# tests/test_auto_grade.py
import unittest
from unittest.mock import patch

# Import the function under test
from services.grading_service import grade_mcq_submission

# --- Mock Data ---

# Define a set of mock questions (Total Marks = 10)
MOCK_MCQ_QUESTIONS = [
    {"question_no": 1, "correct_option": "A", "marks": 5}, # Q1: 5 marks, Correct=A
    {"question_no": 2, "correct_option": "B", "marks": 2}, # Q2: 2 marks, Correct=B
    {"question_no": 3, "correct_option": "C", "marks": 3}, # Q3: 3 marks, Correct=C
] 


class MCQAutoGradingTest(unittest.TestCase):
    
    # We patch the external dependency that fetches the questions from the database.
    @patch('services.grading_service.get_mcq_questions_by_exam')
    def test_01_all_correct(self, mock_get_questions):
        """
        Tests grading logic when all answers are correct.
        Expected: 10/10 marks, 100%
        """
        mock_get_questions.return_value = MOCK_MCQ_QUESTIONS
        
        student_answers = {
            "mcq_1": "A",
            "mcq_2": "B",
            "mcq_3": "C",
        }
        
        result = grade_mcq_submission("exam_id", "student_id", student_answers)
        
        self.assertEqual(result["total_marks"], 10)
        self.assertEqual(result["obtained_marks"], 10)
        self.assertEqual(result["percentage"], 100.0)
        self.assertEqual(result["correct_answers"], 3)
        self.assertEqual(result["incorrect_answers"], 0)
        self.assertEqual(result["unanswered"], 0)

    @patch('services.grading_service.get_mcq_questions_by_exam')
    def test_02_mixed_answers_and_unanswered(self, mock_get_questions):
        """
        Tests grading logic with one correct (5M), one incorrect (0M), and one unanswered (0M).
        Total Marks: 10. Obtained Marks: 5. 
        Expected: 5/10 marks, 50%
        """
        mock_get_questions.return_value = MOCK_MCQ_QUESTIONS
    
        # Q1: Correct (5 marks), Q2: Incorrect (0 marks), Q3: Unanswered (0 marks)
        student_answers = {
            "mcq_1": "A",
            "mcq_2": "X",  # Incorrect answer
        }
    
        result = grade_mcq_submission("exam_id", "student_id", student_answers)
    
        self.assertEqual(result["total_marks"], 10)
        self.assertEqual(result["obtained_marks"], 5)
        self.assertEqual(result["percentage"], 50.0)
        self.assertEqual(result["correct_answers"], 1)
        self.assertEqual(result["incorrect_answers"], 1)
        self.assertEqual(result["unanswered"], 1)
    
        # Verify specific results for Q2 (Incorrect)
        # INDENTATION FIX applied here:
        q2_result = [q for q in result["question_results"] if q["question_no"] == 2][0]
        self.assertFalse(q2_result["is_correct"])
        self.assertEqual(q2_result["marks_obtained"], 0)

    @patch('services.grading_service.get_mcq_questions_by_exam')
    def test_03_empty_exam(self, mock_get_questions):
        """
        Tests the edge case where no MCQ questions exist for the exam.
        """
        mock_get_questions.return_value = [] # Mock returns empty list
        
        student_answers = {"mcq_1": "A"} # Answers are ignored if no questions exist
        
        result = grade_mcq_submission("exam_id", "student_id", student_answers)
        
        self.assertEqual(result["total_marks"], 0)
        self.assertEqual(result["obtained_marks"], 0)
        self.assertEqual(result["percentage"], 0)
        self.assertEqual(result["total_questions"], 0)
        self.assertEqual(result["correct_answers"], 0)


if __name__ == '__main__':
    unittest.main()