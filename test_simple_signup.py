#!/usr/bin/env python3
"""
Simple signup test to isolate the signup error
"""

import json
from core.user_auth import user_auth_manager

def test_signup():
    try:
        print("Testing user creation...")
        result = user_auth_manager.create_user(
            email='simple_test@example.com',
            password='testpass123',
            name='Simple Test'
        )
        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    result = test_signup()
    print(f"Final result: {result}")
