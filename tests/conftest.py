import pytest
from unittest.mock import MagicMock
import sys

# Mock the firebase setup BEFORE importing modules
# This prevents the code from trying to read the certificate file
mock_db = MagicMock()
sys.modules['core.firebase_db'] = MagicMock()
sys.modules['core.firebase_db'].db = mock_db

@pytest.fixture
def mock_firestore():
    """Returns the mocked database object to verify calls in tests"""
    return mock_db