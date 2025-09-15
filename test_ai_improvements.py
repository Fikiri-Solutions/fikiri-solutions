#!/usr/bin/env python3
"""
Test script for AI Assistant improvements
"""

import sys
import os
sys.path.insert(0, '.')

from core.minimal_ai_assistant import MinimalAIEmailAssistant

def test_ai_assistant():
    """Test the improved AI Assistant."""
    print("🧪 Testing AI Assistant Improvements...")
    print("=" * 50)
    
    # Create AI Assistant (without API key to test fallback)
    ai = MinimalAIEmailAssistant()
    
    # Test cases
    test_cases = [
        "how many emails do i have",
        "how many leads do i have", 
        "what's my last email",
        "show me recent customers",
        "help me with email automation",
        "hello",
        "what can you do"
    ]
    
    for test_message in test_cases:
        print(f"\n📝 User: {test_message}")
        response = ai.generate_chat_response(test_message)
        print(f"🤖 AI: {response}")
        print("-" * 30)
    
    print("\n✅ AI Assistant test completed!")

if __name__ == "__main__":
    test_ai_assistant()
