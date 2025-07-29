"""
Tests for security components
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from app.core.security import (
    DataEncryption, 
    AuditLogger, 
    sanitize_input, 
    validate_sql_injection,
    get_client_ip
)


class TestDataEncryption:
    """Test data encryption functionality"""
    
    def test_encrypt_decrypt_cycle(self):
        """Test that data can be encrypted and decrypted correctly"""
        encryption = DataEncryption()
        original_data = "sensitive@email.com"
        
        # Encrypt data
        encrypted_data = encryption.encrypt(original_data)
        assert encrypted_data != original_data
        assert len(encrypted_data) > 0
        
        # Decrypt data
        decrypted_data = encryption.decrypt(encrypted_data)
        assert decrypted_data == original_data
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string"""
        encryption = DataEncryption()
        result = encryption.encrypt("")
        assert result == ""
    
    def test_encrypt_none(self):
        """Test encrypting None value"""
        encryption = DataEncryption()
        result = encryption.encrypt(None)
        assert result is None
    
    def test_decrypt_empty_string(self):
        """Test decrypting empty string"""
        encryption = DataEncryption()
        result = encryption.decrypt("")
        assert result == ""
    
    def test_decrypt_none(self):
        """Test decrypting None value"""
        encryption = DataEncryption()
        result = encryption.decrypt(None)
        assert result is None
    
    def test_hash_data(self):
        """Test data hashing"""
        encryption = DataEncryption()
        data = "test@example.com"
        
        hash1 = encryption.hash_data(data)
        hash2 = encryption.hash_data(data)
        
        # Same data should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 character hex string
        
        # Different data should produce different hash
        hash3 = encryption.hash_data("different@example.com")
        assert hash1 != hash3
    
    def test_hash_empty_string(self):
        """Test hashing empty string"""
        encryption = DataEncryption()
        result = encryption.hash_data("")
        assert result == ""
    
    def test_hash_none(self):
        """Test hashing None value"""
        encryption = DataEncryption()
        result = encryption.hash_data(None)
        assert result is None
    
    def test_different_instances_same_key(self):
        """Test that different encryption instances use the same key"""
        encryption1 = DataEncryption()
        encryption2 = DataEncryption()
        
        data = "test data"
        encrypted1 = encryption1.encrypt(data)
        decrypted2 = encryption2.decrypt(encrypted1)
        
        assert decrypted2 == data


class TestAuditLogger:
    """Test audit logging functionality"""
    
    def test_log_patient_created(self):
        """Test logging patient creation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Create audit logger with custom log file
            audit_logger = AuditLogger()
            
            # Mock the logger to capture log messages
            with patch.object(audit_logger.logger, 'info') as mock_info:
                audit_logger.log_patient_created(
                    patient_id="test-patient-id",
                    user_id="test-user",
                    ip_address="127.0.0.1"
                )
                
                # Verify log was called
                mock_info.assert_called_once()
                log_message = mock_info.call_args[0][0]
                assert "PATIENT_CREATED" in log_message
                assert "test-patient-id" in log_message
                assert "test-user" in log_message
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_log_patient_updated(self):
        """Test logging patient updates"""
        audit_logger = AuditLogger()
        
        with patch.object(audit_logger.logger, 'info') as mock_info:
            changes = {"first_name": "John", "email": "john@example.com"}
            audit_logger.log_patient_updated(
                patient_id="test-patient-id",
                changes=changes,
                user_id="test-user",
                ip_address="127.0.0.1"
            )
            
            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "PATIENT_UPDATED" in log_message
            assert "first_name" in log_message
            assert "email" in log_message
    
    def test_log_patient_accessed(self):
        """Test logging patient access"""
        audit_logger = AuditLogger()
        
        with patch.object(audit_logger.logger, 'info') as mock_info:
            audit_logger.log_patient_accessed(
                patient_id="test-patient-id",
                user_id="test-user",
                ip_address="127.0.0.1"
            )
            
            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "PATIENT_ACCESSED" in log_message
    
    def test_log_patient_search(self):
        """Test logging patient search"""
        audit_logger = AuditLogger()
        
        with patch.object(audit_logger.logger, 'info') as mock_info:
            criteria = {"first_name": "John", "is_active": True}
            audit_logger.log_patient_search(
                criteria=criteria,
                result_count=5,
                user_id="test-user",
                ip_address="127.0.0.1"
            )
            
            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "PATIENT_SEARCH" in log_message
            assert "result_count" in log_message
    
    def test_log_patient_deactivated(self):
        """Test logging patient deactivation"""
        audit_logger = AuditLogger()
        
        with patch.object(audit_logger.logger, 'info') as mock_info:
            audit_logger.log_patient_deactivated(
                patient_id="test-patient-id",
                user_id="test-user",
                ip_address="127.0.0.1"
            )
            
            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "PATIENT_DEACTIVATED" in log_message


class TestSecurityUtilities:
    """Test security utility functions"""
    
    def test_sanitize_input_normal_text(self):
        """Test sanitizing normal text"""
        clean_text = "John Doe"
        result = sanitize_input(clean_text)
        assert result == clean_text
    
    def test_sanitize_input_dangerous_characters(self):
        """Test sanitizing text with dangerous characters"""
        dangerous_text = "John<script>alert('xss')</script>Doe"
        result = sanitize_input(dangerous_text)
        assert "<script>" not in result
        assert "alert" in result  # Content should remain, just tags removed
        assert "Doe" in result
    
    def test_sanitize_input_empty_string(self):
        """Test sanitizing empty string"""
        result = sanitize_input("")
        assert result == ""
    
    def test_sanitize_input_none(self):
        """Test sanitizing None value"""
        result = sanitize_input(None)
        assert result is None
    
    def test_sanitize_input_length_limit(self):
        """Test that input is limited to reasonable length"""
        long_text = "a" * 2000  # Very long text
        result = sanitize_input(long_text)
        assert len(result) <= 1000
    
    def test_validate_sql_injection_safe_params(self):
        """Test SQL injection validation with safe parameters"""
        safe_params = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "age": 30
        }
        result = validate_sql_injection(safe_params)
        assert result is True
    
    def test_validate_sql_injection_dangerous_params(self):
        """Test SQL injection validation with dangerous parameters"""
        dangerous_params = {
            "first_name": "John'; DROP TABLE patients; --",
            "email": "john@example.com"
        }
        result = validate_sql_injection(dangerous_params)
        assert result is False
        
        # Test other dangerous patterns
        patterns_to_test = [
            {"query": "SELECT * FROM users"},
            {"input": "1 UNION SELECT password FROM users"},
            {"data": "'; INSERT INTO admin VALUES ('hacker'); --"},
            {"field": "1' OR '1'='1"},
            {"value": "exec xp_cmdshell('dir')"}
        ]
        
        for params in patterns_to_test:
            result = validate_sql_injection(params)
            assert result is False
    
    def test_validate_sql_injection_mixed_params(self):
        """Test SQL injection validation with mixed safe/dangerous parameters"""
        mixed_params = {
            "safe_field": "John Doe",
            "dangerous_field": "'; DROP TABLE users; --",
            "another_safe_field": "john@example.com"
        }
        result = validate_sql_injection(mixed_params)
        assert result is False  # Should fail if any field is dangerous
    
    def test_get_client_ip_direct(self):
        """Test getting client IP from direct connection"""
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.100"
        
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.100"
    
    def test_get_client_ip_forwarded(self):
        """Test getting client IP from X-Forwarded-For header"""
        mock_request = Mock()
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.1, 192.168.1.100"
        }
        mock_request.client.host = "192.168.1.100"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"  # Should get the first IP from forwarded header
    
    def test_get_client_ip_real_ip(self):
        """Test getting client IP from X-Real-IP header"""
        mock_request = Mock()
        mock_request.headers = {
            "X-Real-IP": "203.0.113.2"
        }
        mock_request.client.host = "192.168.1.100"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.2"
    
    def test_get_client_ip_no_client(self):
        """Test getting client IP when client info is not available"""
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = None
        
        ip = get_client_ip(mock_request)
        assert ip == "unknown"
    
    def test_get_client_ip_priority(self):
        """Test that X-Forwarded-For takes priority over X-Real-IP"""
        mock_request = Mock()
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "203.0.113.2"
        }
        mock_request.client.host = "192.168.1.100"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"  # X-Forwarded-For should take priority