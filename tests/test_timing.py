# tests/test_timing.py
import pytest
from datetime import datetime, timedelta, timezone
from services import exam_timing

# Define Malaysia TZ for testing
MALAYSIA_TZ = timezone(timedelta(hours=8))

def test_calculate_exam_window():
    """Test if start and end times are calculated correctly"""
    start = datetime(2025, 11, 28, 10, 0, tzinfo=MALAYSIA_TZ)
    duration = 60
    
    start_time, end_time = exam_timing.calculate_exam_window(start, duration)
    
    assert start_time == start
    assert end_time == start + timedelta(minutes=60)

def test_exam_access_before_start(mocker, mock_firestore):
    """Test access denied before exam starts"""
    # 1. Setup Data
    exam_id = "exam_123"
    exam_start = datetime(2025, 12, 1, 10, 0, tzinfo=MALAYSIA_TZ)
    
    # 2. Mock DB response
    mock_exam_doc = {
        "status": "published",
        "exam_date": "2025-12-01",
        "start_time": "10:00",
        "duration": 60
    }
    # Setup the mock chain: db.collection().document().get().to_dict()
    mock_firestore.collection.return_value.document.return_value.get.return_value.exists = True
    mock_firestore.collection.return_value.document.return_value.get.return_value.to_dict.return_value = mock_exam_doc

    # 3. Freeze Server Time to 9:00 AM (1 hour before exam)
    current_time = datetime(2025, 12, 1, 9, 0, tzinfo=MALAYSIA_TZ)
    mocker.patch('services.exam_timing.get_server_time', return_value=current_time)

    # 4. Run Function
    result = exam_timing.check_exam_access(exam_id)

    # 5. Assertions
    assert result['can_access'] is False
    assert result['status'] == 'before_start'
    assert "will start in 60 minutes" in result['message']