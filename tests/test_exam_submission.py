from web import student_exam


def test_submit_exam_success(mocker, mock_firestore):
    """
    Scenario: Student submits valid answers for the first time.
    """
    body_data = (
        "exam_id=exam_001&student_id=std_123&answers=%7B%22mcq_1%22%3A%22A%22%7D"
    )

    # --- MOCKS ---
    # 1. Mock DB check (Not submitted yet)
    mocker.patch(
        "web.student_exam.check_student_submission_status",
        return_value={"has_submitted": False},
    )

    # 2. Mock Grading Service
    mocker.patch("services.grading_service.grade_mcq_submission", return_value={})
    mocker.patch("services.grading_service.save_grading_result", return_value=True)
    mocker.patch("web.student_exam.get_server_time")

    # 3. [NEW] Mock Render so we don't look for HTML files
    # We fake it returning a success message
    mocker.patch(
        "web.student_exam.render", return_value="<html>Grading your exam...</html>"
    )

    # --- EXECUTE ---
    response_html, status_code = student_exam.post_submit_student_exam(body_data)

    # --- ASSERT ---
    assert status_code == 200
    # Since we mocked render, we check if our mocked return value exists
    assert "Grading your exam" in response_html

    # Check if DB was called
    assert mock_firestore.collection.call_args[0][0] == "submissions"
    mock_firestore.collection.return_value.document.return_value.set.assert_called_once()


def test_prevent_duplicate_submission(mocker):
    """
    Scenario: Student tries to submit twice.
    """
    body_data = "exam_id=exam_001&student_id=std_123"

    # --- MOCKS ---
    # 1. Mock DB check (ALREADY Submitted)
    mocker.patch(
        "web.student_exam.check_student_submission_status",
        return_value={"has_submitted": True},
    )

    # 2. [NEW] Mock Render to avoid FileNotFoundError for 'error.html'
    mocker.patch(
        "web.student_exam.render",
        return_value="<html>Error: You have already submitted</html>",
    )

    # --- EXECUTE ---
    response_html, status_code = student_exam.post_submit_student_exam(body_data)

    # --- ASSERT ---
    assert status_code == 400
    assert "already submitted" in response_html
