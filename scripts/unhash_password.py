#!/usr/bin/env python3
"""
Password Unhashing Script

This script attempts to find the original password from a bcrypt hash.
Since bcrypt is one-way, it works by testing common passwords against the hash.

Usage:
    python unhash_password.py <hash_value>

Example:
    python unhash_password.py "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uO8e"

Note: Make sure to run this script from the project root directory.
"""

import sys
import os
import warnings
import time

# Suppress bcrypt version warning
warnings.filterwarnings("ignore", category=UserWarning)

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import after setting up path
from utils.security import verify_password

def find_password(hash_value: str) -> str:
    """Attempt to find the password by testing common passwords against the hash."""
    
    # Extended list of common passwords to test
    common_passwords = [
        # Very common passwords
        "password", "123456", "123456789", "qwerty", "abc123",
        "password123", "admin", "letmein", "welcome", "monkey",
        "dragon", "master", "football", "superman", "trustno1",
        "jordan", "michael", "shadow", "mustang", "baseball",
        "access", "flower", "hello", "secret", "mike",
        "jordan23", "password1", "admin123", "12345678", "qwerty123",
        "letmein123", "welcome123", "monkey123", "dragon123", "master123",
        
        # More variations
        "test", "guest", "user", "demo", "sample", "example",
        "default", "root", "system", "server", "database", "mysql",
        "oracle", "postgres", "mongo", "redis", "elastic", "kafka",
        "docker", "kubernetes", "jenkins", "gitlab", "github", "bitbucket",
        
        # Common names
        "john", "jane", "mike", "sarah", "david", "lisa", "tom", "amy",
        "chris", "emma", "alex", "sam", "jessica", "matt", "rachel",
        "daniel", "emily", "josh", "ashley", "ryan", "stephanie",
        
        # Common words
        "love", "hate", "good", "bad", "yes", "no", "maybe", "okay",
        "cool", "awesome", "great", "nice", "fine", "ok", "sure",
        "right", "wrong", "true", "false", "on", "off", "up", "down",
        
        # Tech terms
        "computer", "laptop", "phone", "tablet", "internet", "network",
        "server", "client", "api", "rest", "graphql", "json", "xml",
        "html", "css", "javascript", "python", "java", "c++", "php",
        "ruby", "go", "rust", "swift", "kotlin", "scala", "r",
        
        # Simple patterns
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
        "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
        "aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh", "ii", "jj",
        "kk", "ll", "mm", "nn", "oo", "pp", "qq", "rr", "ss", "tt",
        "uu", "vv", "ww", "xx", "yy", "zz",
        
        # Numbers
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "00", "01", "02", "03", "04", "05", "06", "07", "08", "09",
        "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
        "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
        "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
        "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
        "60", "61", "62", "63", "64", "65", "66", "67", "68", "69",
        "70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
        "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
        "90", "91", "92", "93", "94", "95", "96", "97", "98", "99",
        
        # Common combinations
        "password123", "admin123", "user123", "test123", "demo123",
        "guest123", "root123", "system123", "server123", "mysql123",
        "oracle123", "postgres123", "mongo123", "redis123", "docker123",
        "jenkins123", "gitlab123", "github123", "bitbucket123",
        
        # Year variations
        "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017",
        "2016", "2015", "2014", "2013", "2012", "2011", "2010",
        "2009", "2008", "2007", "2006", "2005", "2004", "2003",
        "2002", "2001", "2000", "1999", "1998", "1997", "1996",
        
        # Month variations
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
        
        # Day variations
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "mon", "tue", "wed", "thu", "fri", "sat", "sun",
        
        # Common phrases
        "hello world", "good morning", "good night", "good bye", "see you",
        "thank you", "you're welcome", "excuse me", "i'm sorry", "no problem",
        "of course", "absolutely", "definitely", "certainly", "sure thing",
        
        # Empty and whitespace
        "", " ", "  ", "   ", "    ", "     "
    ]
    
    print(f"🔍 Attempting to find password for hash: {hash_value[:30]}...")
    print(f"⏳ Testing {len(common_passwords)} passwords...")
    
    start_time = time.time()
    
    for i, password in enumerate(common_passwords, 1):
        if verify_password(password, hash_value):
            elapsed = time.time() - start_time
            print(f"\n🎉 Password found after {i} attempts!")
            print(f"⏱️  Time taken: {elapsed:.2f} seconds")
            return password
        
        # Show progress every 10 attempts
        if i % 10 == 0:
            print(f"   Tested {i}/{len(common_passwords)} passwords...")
    
    elapsed = time.time() - start_time
    print(f"\n❌ Password not found in common password list")
    print(f"⏱️  Time taken: {elapsed:.2f} seconds")
    return "Password not found in common list"

def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    hash_value = sys.argv[1]
    
    try:
        # Validate hash format
        if not hash_value.startswith('$2b$') and not hash_value.startswith('$2a$'):
            print("❌ Error: This doesn't appear to be a valid bcrypt hash")
            print("   Bcrypt hashes should start with $2b$ or $2a$")
            sys.exit(1)
        
        # Find the password
        password = find_password(hash_value)
        
        # Print the result
        print(f"\n📋 Result:")
        print(f"   Hash: {hash_value}")
        print(f"   Password: {password}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
