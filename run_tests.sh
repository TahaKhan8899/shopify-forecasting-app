#!/bin/bash

# Shell script to run all tests and generate a report

echo "====================================================================="
echo "        SHOPIFY DATA FORECASTING APP - TEST RUNNER"
echo "====================================================================="
echo "Starting tests at $(date)"
echo

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install test dependencies
echo "Installing test dependencies..."
pip install -r tests/requirements.txt > /dev/null
pip install -r requirements.txt > /dev/null

# Run tests
echo "Running tests..."
python tests/run_tests.py

# Capture exit code
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

echo 
echo "Tests completed at $(date)"
echo "====================================================================="

exit $EXIT_CODE 