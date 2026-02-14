#!/usr/bin/env python3
"""
Run Public API Tests
Test runner for public API functionality
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_tests():
    """Run all public API tests"""
    # Suppresses "missing OpenAI API key" warnings in llm_client and ai_assistant
    os.environ.setdefault("FIKIRI_TEST_MODE", "1")

    # Discover and run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test modules
    suite.addTests(loader.loadTestsFromName('tests.test_api_key_manager'))
    suite.addTests(loader.loadTestsFromName('tests.test_public_chatbot_api'))
    suite.addTests(loader.loadTestsFromName('tests.test_ai_analysis_api'))
    suite.addTests(loader.loadTestsFromName('tests.test_vector_persistence'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests())
