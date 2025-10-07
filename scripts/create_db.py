#!/usr/bin/env python3
"""
Script to create the SQLite database for the nutritional misinformation survey app.
"""

import os
import sys

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import init_db

if __name__ == "__main__":
    # Remove existing database file if it exists
    db_path = "data/survey.db"
    if os.path.exists(db_path):
        print(f"Removing existing database file: {db_path}")
        os.remove(db_path)
    
    # Create a new database
    print("Creating new database...")
    init_db()
    
    print(f"Database created at {os.path.abspath(db_path)}")
    print("Database structure:")
    print("- participants table")
    print("- recipe_evaluations table")
    print("- post_surveys table")
