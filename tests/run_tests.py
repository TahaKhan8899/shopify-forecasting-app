#!/usr/bin/env python3
"""
Test runner script to execute all unit tests for the forecasting app.
"""

import unittest
import sys
import os
import time
import datetime

def run_tests():
    """Discover and run all tests in the tests directory."""
    # Add the parent directory to the path to make imports work
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    
    # Start the timer
    start_time = time.time()
    
    # Discover and run tests
    loader = unittest.TestLoader()
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(tests_dir)
    
    # Run the tests with a test runner that captures results
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    
    # End the timer
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Print test summary report
    print("\n" + "=" * 70)
    print("TEST SUMMARY REPORT")
    print("=" * 70)
    
    # Get counts
    total_tests = test_result.testsRun
    failures = len(test_result.failures)
    errors = len(test_result.errors)
    skipped = len(test_result.skipped)
    successful = total_tests - failures - errors - skipped
    
    # Calculate success rate
    success_rate = (successful / total_tests) * 100 if total_tests > 0 else 0
    
    # Print summary metrics
    print(f"Date:          {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Tests:   {total_tests}")
    print(f"Successful:    {successful}")
    print(f"Failures:      {failures}")
    print(f"Errors:        {errors}")
    print(f"Skipped:       {skipped}")
    print(f"Success Rate:  {success_rate:.2f}%")
    print(f"Execution Time: {execution_time:.2f} seconds")
    print("=" * 70)
    
    # List failed tests if any
    if failures > 0 or errors > 0:
        print("\nFAILED TESTS:")
        print("-" * 70)
        
        # Print failures
        for i, (test, traceback) in enumerate(test_result.failures):
            print(f"{i+1}. FAILURE: {test}")
            
        # Print errors
        for i, (test, traceback) in enumerate(test_result.errors):
            print(f"{i+1}. ERROR: {test}")
        
        print("-" * 70)
    
    # Return appropriate exit code
    return 0 if test_result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 