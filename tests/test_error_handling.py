"""
Tests for error handling, input validation, and sanitization.
"""
import pytest
from fastapi.testclient import TestClient
import uuid
from unittest.mock import patch

from app.main import app
from app.db.database import get_db
from app.core.security import sanitize_input, validate_sql_injection
from tests.conftest import override_get_db


@pytest.fixture
def client():
    """Test client with database dependency override"""
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


class TestErrorHandling:
    """Test error handling and response formatting"""
    
    def test_validation_error_format(self, client):
        """Test validation error response format"""
        # Invalid data
        invalid_data = {
            "username": "u",  # Too short
            "password": "short",  # Too short
            "email": "not-an-email"  # Invalid format
        }
        
        # Attempt to register with invalid data
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        # Verify response format
        assert response.status_code == 422
        error_data = response.json()
        
        # Check for standard error format
        assert "detail" in error_data
        
        # Alternative format with our custom handler
        if isinstance(error_data, dict) and "error_code" in error_data:
            assert error_data["success"] is False
            assert error_data["error_code"] == "VALIDATION_ERROR"
            assert "validation_errors" in error_data["details"]
    
    def test_not_found_error(self, client):
        """Test 404 error handling"""
        # Non-existent endpoint
        response = client.get("/api/v1/non-existent")
        
        assert response.status_code == 404
        error_data = response.json()
        
        # Check for standard error format
        assert "detail" in error_data
    
    def test_correlation_id_in_responses(self, client):
        """Test correlation ID is included in responses"""
        # Make any request
        response = client.get("/api/v1/")
        
        # Check for correlation ID header
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] != ""
    
    def test_internal_server_error_handling(self, client):
        """Test handling of internal server errors"""
        # Mock an internal server error
        with patch("app.api.v1.api.api_root") as mock_api_root:
            mock_api_root.side_effect = Exception("Simulated internal error")
            
            response = client.get("/api/v1/")
            
            assert response.status_code == 500
            error_data = response.json()
            
            # Check that we don't expose internal error details
            assert "Simulated internal error" not in str(error_data)
            
            # Check for standard error format
            if "error_code" in error_data:
                assert error_data["error_code"] == "INTERNAL_SERVER_ERROR"
                assert "request_id" in error_data


class TestInputSanitization:
    """Test input sanitization and SQL injection prevention"""
    
    def test_sanitize_input(self):
        """Test input sanitization function"""
        # Test with potentially dangerous input
        dangerous_input = "<script>alert('XSS');</script>"
        sanitized = sanitize_input(dangerous_input)
        
        assert "<script>" not in sanitized
        assert "alert" in sanitized  # Content preserved
        assert "XSS" in sanitized  # Content preserved
        
        # Test with SQL injection attempt
        sql_injection = "'; DROP TABLE users; --"
        sanitized = sanitize_input(sql_injection)
        
        assert "'" not in sanitized
        assert ";" not in sanitized
    
    def test_validate_sql_injection(self):
        """Test SQL injection validation"""
        # Safe parameters
        safe_params = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }
        assert validate_sql_injection(safe_params) is True
        
        # Dangerous parameters
        dangerous_params = {
            "name": "John'; DROP TABLE users; --",
            "age": 30
        }
        assert validate_sql_injection(dangerous_params) is False
        
        # Test with more SQL injection patterns
        injection_patterns = [
            {"query": "SELECT * FROM users"},
            {"search": "1 UNION SELECT password FROM users"},
            {"filter": "admin' OR '1'='1"},
            {"sort": "name; DELETE FROM users"}
        ]
        
        for params in injection_patterns:
            assert validate_sql_injection(params) is False
    
    def test_sanitization_in_api(self, client):
        """Test sanitization in API endpoints"""
        # Create a search with potentially dangerous input
        response = client.get(
            "/api/v1/patients/search",
            params={"first_name": "<script>alert('XSS');</script>"}
        )
        
        # Should return 401 because we're not authenticated, not 500
        assert response.status_code == 401 