from web import student_exam


def test_render_mcq_questions(mocker):
    """
    Scenario: Exam has MCQ questions.
    Expected: HTML should contain the question text and radio options.
    """
    exam_id = "exam_mcq_01"

    mock_questions = [
        {
            "question_no": 1,
            "question_text": "What is the capital of Malaysia?",
            "marks": 5,
            "options": {"A": "Ipoh", "B": "Kuala Lumpur", "C": "Penang", "D": "Johor"},
        }
    ]

    # Patch where it is imported in web.student_exam
    mocker.patch(
        "web.student_exam.get_mcq_questions_by_exam", return_value=mock_questions
    )
    mocker.patch("web.student_exam.get_short_answer_questions_by_exam", return_value=[])

    html_output = student_exam._build_questions_html(exam_id)

    assert "What is the capital of Malaysia?" in html_output
    assert 'value="B"' in html_output


def test_render_no_questions(mocker):
    mocker.patch("web.student_exam.get_mcq_questions_by_exam", return_value=[])
    mocker.patch("web.student_exam.get_short_answer_questions_by_exam", return_value=[])

    html_output = student_exam._build_questions_html("exam_empty")

    assert "No questions available" in html_output
