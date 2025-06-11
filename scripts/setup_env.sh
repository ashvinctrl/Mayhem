#!/bin/bash

# This script sets up the development environment for Project Mayhem

# Update package list and install necessary packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt

# Additional setup steps can be added here

echo "Development environment setup complete. Activate the virtual environment using 'source venv/bin/activate'."