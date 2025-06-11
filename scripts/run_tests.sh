#!/bin/bash

# Navigate to the source directory
cd src

# Run all tests in the tests directory
pytest tests/ --maxfail=1 --disable-warnings -q

# Check the exit status of the tests
if [ $? -eq 0 ]; then
    echo "All tests passed successfully!"
else
    echo "Some tests failed. Please check the output above."
fi