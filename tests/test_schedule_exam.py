# tests/test_schedule_exam.py
import unittest
# Import the function directly from the file you provided
from core.validation import validate_exam_times 

class ExamTimeValidationTest(unittest.TestCase):
    """
    Tests the validation logic for exam start time, end time, and duration
    to ensure they are consistent, handling same-day and cross-midnight scenarios.
    """

    # --- Test 1: Perfect Consistency (Standard Same-Day Case) ---
    def test_times_valid_standard(self):
        """Test for a perfectly consistent, 90-minute, same-day exam (10:00 to 11:30)."""
        start_time = "10:00"
        end_time = "11:30"
        duration = "90" # 90 minutes
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertEqual(errors, [], "Should have no errors for a consistent, standard exam.")

    # --- Test 2: Perfect Consistency (Cross Midnight Case) ---
    def test_times_valid_cross_midnight(self):
        """Test for a perfectly consistent, 120-minute (2 hour) exam that crosses midnight (23:00 to 01:00)."""
        start_time = "23:00"
        end_time = "01:00"
        duration = "120" # 120 minutes 
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertEqual(errors, [], "Should have no errors for a consistent, cross-midnight exam.")

    # --- Test 3: Incorrect Duration (Too Short) ---
    def test_times_inconsistent_duration_short(self):
        """Test case where the specified duration (30 mins) is shorter than the actual duration (60 mins)."""
        start_time = "14:00"
        end_time = "15:00" # 60 minutes apart
        duration = "30" 
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertNotEqual(errors, [], "Should detect inconsistency.")
        self.assertIn("Time mismatch:", errors[0])
        
    # --- Test 4: Incorrect Duration (Too Long) ---
    def test_times_inconsistent_duration_long(self):
        """Test case where the specified duration (120 mins) is longer than the actual duration (60 mins)."""
        start_time = "09:00"
        end_time = "10:00" # 60 minutes apart
        duration = "120" 
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertNotEqual(errors, [], "Should detect inconsistency.")
        self.assertIn("Time mismatch:", errors[0])

    # --- Test 5: Missing Start Time ---
    def test_times_missing_start_time(self):
        """Test case for missing required field: start_time."""
        start_time = ""
        end_time = "15:00"
        duration = "60"
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertIn("Start time is required.", errors)

    # --- Test 6: Invalid Time Format ---
    def test_times_invalid_format(self):
        """Test case for a poorly formatted time field (10-00 instead of 10:00)."""
        start_time = "10-00"
        end_time = "11:00"
        duration = "60"
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertIn("Invalid time format.", errors)
        
    # --- Test 7: Handling small rounding discrepancy (e.g., 1-minute tolerance) ---
    def test_times_small_discrepancy_allowed(self):
        """Test where duration is off by exactly 1 minute, which should be allowed."""
        # 10:00 to 11:31 is 91 minutes. Providing 90 should be tolerated by the implementation.
        start_time = "10:00"
        end_time = "11:31"
        duration = "90"
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertEqual(errors, [], "Discrepancy of 1 minute should be allowed.")

    # --- Test 8: Discrepancy outside tolerance (2 minutes) ---
    def test_times_discrepancy_not_allowed(self):
        """Test where duration is off by 2 minutes, which should trigger an error."""
        # 10:00 to 11:32 is 92 minutes. Providing 90 should NOT be tolerated.
        start_time = "10:00"
        end_time = "11:32"
        duration = "90"
        
        errors = validate_exam_times(start_time, end_time, duration)
        
        self.assertIn("Time mismatch:", errors[0])


if __name__ == '__main__':
    unittest.main()