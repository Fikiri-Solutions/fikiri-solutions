#!/usr/bin/env python3
"""
Password hashing test to verify authentication system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.user_auth import UserAuthManager

def test_password_hashing():
    """Test password hashing and verification"""
    print("🔑 TESTING PASSWORD HASHING")
    print("=" * 40)
    
    # Create authenticator instance
    auth = UserAuthManager()
    
    # Test password
    test_password = "testpass123"
    
    # Hash password
    password_hash, salt = auth._hash_password(test_password)
    print(f"✅ Password hashed successfully")
    print(f"Hash: {password_hash[:20]}...")
    print(f"Salt: {salt[:20]}...")
    
    # Verify password
    is_valid = auth._verify_password(test_password, password_hash, salt)
    print(f"✅ Password verification: {is_valid}")
    
    # Test wrong password
    is_invalid = auth._verify_password("wrongpassword", password_hash, salt)
    print(f"✅ Wrong password verification: {is_invalid}")
    
    if is_valid and not is_invalid:
        print("🎉 Password hashing system is working correctly!")
        return True
    else:
        print("❌ Password hashing system has issues!")
        return False

if __name__ == "__main__":
    test_password_hashing()
