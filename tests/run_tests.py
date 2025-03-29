#!/usr/bin/env python3
"""
Test runner script to execute all unit tests for the forecasting app.
"""

import unittest
import sys
import os

def run_tests():
    """Discover and run all tests in the tests directory."""
    # Add the parent directory to the path to make imports work
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(tests_dir)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 