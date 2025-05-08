#!/usr/bin/env python3
"""
Password Hashing Script

This script takes a password as input and outputs its bcrypt hash.
The hash can be used for storing passwords securely in the database.

Usage:
    python hash_password.py <password>
    ./hash_password.py <password>

Example:
    python hash_password.py "mysecurepassword123"
    ./hash_password.py "mysecurepassword123"

Note: Make sure to run this script from the project root directory.
"""

import sys
import os
import warnings

# Suppress bcrypt version warning
warnings.filterwarnings("ignore", category=UserWarning)

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import after setting up path
from config import pwd_context
from utils.security import get_password_hash

def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    try:
        password = sys.argv[1]
        hashed_password = get_password_hash(password)
        print(f"Hashed password: {hashed_password}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 