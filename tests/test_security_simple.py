"""
Simple tests for security components without database dependencies
"""
from app.core.security import DataEncryption, sanitize_input, validate_sql_injection


def test_data_encryption():
    """Test data encryption and decryption"""
    encryption = DataEncryption()
    original_data = "sensitive@email.com"
    
    # Encrypt data
    encrypted_data = encryption.encrypt(original_data)
    assert encrypted_data != original_data
    assert len(encrypted_data) > 0
    
    # Decrypt data
    decrypted_data = encryption.decrypt(encrypted_data)
    assert decrypted_data == original_data
    print("✓ Data encryption/decryption works")


def test_data_hashing():
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
    print("✓ Data hashing works")


def test_input_sanitization():
    """Test input sanitization"""
    # Normal text should pass through
    clean_text = "John Doe"
    result = sanitize_input(clean_text)
    assert result == clean_text
    
    # Dangerous characters should be removed
    dangerous_text = "John<script>alert('xss')</script>Doe"
    result = sanitize_input(dangerous_text)
    assert "<script>" not in result
    assert "alert" in result  # Content should remain, just tags removed
    assert "Doe" in result
    
    # Empty string and None should be handled
    assert sanitize_input("") == ""
    assert sanitize_input(None) is None
    print("✓ Input sanitization works")


def test_sql_injection_validation():
    """Test SQL injection validation"""
    # Safe parameters should pass
    safe_params = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "age": 30
    }
    assert validate_sql_injection(safe_params) is True
    
    # Dangerous parameters should fail
    dangerous_params = {
        "first_name": "John'; DROP TABLE patients; --",
        "email": "john@example.com"
    }
    assert validate_sql_injection(dangerous_params) is False
    
    # Test other dangerous patterns
    patterns_to_test = [
        {"query": "SELECT * FROM users"},
        {"input": "1 UNION SELECT password FROM users"},
        {"data": "'; INSERT INTO admin VALUES ('hacker'); --"},
        {"value": "exec xp_cmdshell('dir')"}
    ]
    
    for params in patterns_to_test:
        result = validate_sql_injection(params)
        assert result is False, f"Pattern should be detected as dangerous: {params}"
    
    print("✓ SQL injection validation works")


if __name__ == "__main__":
    test_data_encryption()
    test_data_hashing()
    test_input_sanitization()
    test_sql_injection_validation()
    print("All security tests passed!")