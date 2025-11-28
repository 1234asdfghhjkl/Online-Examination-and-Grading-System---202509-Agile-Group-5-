from datetime import datetime, timedelta, timezone
from services import exam_timing


MALAYSIA_TZ = timezone(timedelta(hours=8))


def test_exam_active_timer_calculation(mocker, mock_firestore):
    """
    Scenario: Exam is active. Current time is 15 mins into a 60 min exam.
    Expected: Status is 'active' and time_remaining is 45 mins (2700 seconds).
    """
    exam_id = "exam_timer_01"

    # 1. Mock DB Response
    mock_exam_doc = {
        "status": "published",
        "exam_date": "2025-12-01",
        "start_time": "10:00",
        "duration": 60,
    }

    # Setup mock chain
    mock_firestore.collection.return_value.document.return_value.get.return_value.exists = (
        True
    )
    mock_firestore.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
        mock_exam_doc
    )

    # 2. Mock Server Time: 10:15 AM (15 mins elapsed)
    current_time = datetime(2025, 12, 1, 10, 15, tzinfo=MALAYSIA_TZ)
    mocker.patch("services.exam_timing.get_server_time", return_value=current_time)

    # 3. Execute
    result = exam_timing.check_exam_access(exam_id)

    # 4. Assertions
    assert result["can_access"] is True
    assert result["status"] == "active"

    # We expect 45 minutes remaining (60 - 15)
    # 45 minutes * 60 seconds = 2700 seconds
    assert result["time_remaining"] == 2700


def test_exam_ended_timer(mocker, mock_firestore):
    """
    Scenario: Current time is AFTER the exam end time.
    Expected: Status is 'ended', access denied.
    """
    mock_exam_doc = {
        "status": "published",
        "exam_date": "2025-12-01",
        "start_time": "10:00",
        "duration": 60,
    }

    mock_firestore.collection.return_value.document.return_value.get.return_value.exists = (
        True
    )
    mock_firestore.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
        mock_exam_doc
    )

    # Mock Server Time: 11:01 AM (1 minute late)
    current_time = datetime(2025, 12, 1, 11, 1, tzinfo=MALAYSIA_TZ)
    mocker.patch("services.exam_timing.get_server_time", return_value=current_time)

    result = exam_timing.check_exam_access("exam_ended")

    assert result["can_access"] is False
    assert result["status"] == "ended"
    assert result["time_remaining"] == 0
