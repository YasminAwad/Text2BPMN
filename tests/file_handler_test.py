"""
Unit tests for file handler module.
"""

import unittest
import tempfile
import os

from src.utils.file_handler import (
    validate_description,
    read_file
)

from src.exceptions import FileHandlerError


class TestFileHandler(unittest.TestCase):
    """Test cases for file handler functions."""
    
    def test_validate_description_valid(self):
        """Test validation of valid description."""
        description = "This is a valid process description with enough content."
        result = validate_description(description)
        self.assertEqual(result, description)
    
    def test_validate_description_empty(self):
        """Test validation rejects empty description."""
        with self.assertRaises(FileHandlerError):
            validate_description("")
    
    def test_validate_description_too_short(self):
        """Test validation rejects too short description."""
        with self.assertRaises(FileHandlerError):
            validate_description("short")
    
    def test_validate_description_too_long(self):
        """Test validation rejects too long description."""
        with self.assertRaises(FileHandlerError):
            validate_description("x" * 10001)
    
    def test_read_file_success(self):
        """Test reading a valid file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test process description content")
            temp_path = f.name
        
        try:
            content = read_file(temp_path)
            self.assertEqual(content, "Test process description content")
        finally:
            os.unlink(temp_path)
    
    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        with self.assertRaises(FileHandlerError):
            read_file("nonexistent_file.txt")
    
    def test_read_file_unsupported_extension(self):
        """Test reading file with unsupported extension."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("content")
            temp_path = f.name
        
        try:
            with self.assertRaises(FileHandlerError):
                read_file(temp_path)
        finally:
            os.unlink(temp_path)
    
if __name__ == '__main__':
    unittest.main()