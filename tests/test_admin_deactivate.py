import unittest
from unittest.mock import MagicMock

from services.deactivate_service import (
    deactivate_lecturer_by_id,
    reactivate_lecturer_by_id,
    deactivate_student_by_id,
    reactivate_student_by_id,
)


class TestAdminDeactivate(unittest.TestCase):

    # ------------- Lecturer -------------
    def test_deactivate_lecturer_success(self):
        mock_doc = MagicMock()
        mock_doc.reference.update = MagicMock()
        mock_users = MagicMock()
        mock_users.where.return_value.limit.return_value.get.return_value = [mock_doc]

        result = deactivate_lecturer_by_id(
            "L001", MagicMock(collection=lambda _: mock_users)
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "User deactivated")
        mock_doc.reference.update.assert_called_once_with(
            {"is_active": False, "status": "inactive"}
        )

    def test_reactivate_lecturer_success(self):
        mock_doc = MagicMock()
        mock_doc.reference.update = MagicMock()
        mock_users = MagicMock()
        mock_users.where.return_value.limit.return_value.get.return_value = [mock_doc]

        result = reactivate_lecturer_by_id(
            "L001", MagicMock(collection=lambda _: mock_users)
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "User reactivated")
        mock_doc.reference.update.assert_called_once_with(
            {"is_active": True, "status": "active"}
        )

    # ------------- Student -------------
    def test_deactivate_student_success(self):
        mock_doc = MagicMock()
        mock_doc.reference.update = MagicMock()
        mock_users = MagicMock()
        mock_users.where.return_value.limit.return_value.get.return_value = [mock_doc]

        result = deactivate_student_by_id(
            "S101", MagicMock(collection=lambda _: mock_users)
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "User deactivated")
        mock_doc.reference.update.assert_called_once_with(
            {"is_active": False, "status": "inactive"}
        )

    def test_reactivate_student_success(self):
        mock_doc = MagicMock()
        mock_doc.reference.update = MagicMock()
        mock_users = MagicMock()
        mock_users.where.return_value.limit.return_value.get.return_value = [mock_doc]

        result = reactivate_student_by_id(
            "S101", MagicMock(collection=lambda _: mock_users)
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "User reactivated")
        mock_doc.reference.update.assert_called_once_with(
            {"is_active": True, "status": "active"}
        )

    # ------------- Edge cases -------------
    def test_lecturer_not_found(self):
        mock_users = MagicMock()
        mock_users.where.return_value.limit.return_value.get.return_value = []

        result = deactivate_lecturer_by_id(
            "L999", MagicMock(collection=lambda _: mock_users)
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "User not found")

    def test_student_not_found(self):
        mock_users = MagicMock()
        mock_users.where.return_value.limit.return_value.get.return_value = []

        result = reactivate_student_by_id(
            "S999", MagicMock(collection=lambda _: mock_users)
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "User not found")


if __name__ == "__main__":
    unittest.main()
