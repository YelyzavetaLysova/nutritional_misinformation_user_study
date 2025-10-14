#!/usr/bin/env python3
"""
Script to recreate the database with the updated schema.
This will drop the existing database and create a new one with the latest structure.

DATABASE SCHEMA OVERVIEW:
=========================

1. PARTICIPANTS TABLE:
   - Basic participant info with Prolific integration
   - Fields: participant_id, prolific_pid, study_id, session_id, start_time, completed_time, 
     completed, time_spent_minutes, age, gender, education

2. RECIPE_EVALUATIONS TABLE:
   - 8-question format for recipe evaluation + attention check
   - Fields: completeness_rating, healthiness_rating, tastiness_rating, feasibility_rating,
     would_make, ingredients_complexity, instructions_complexity, ingredients_correctness,
     instructions_correctness, nutrition_correctness, comments, attention_check_recipe

3. POST_SURVEYS TABLE:
   - Updated post-survey questions + attention check
   - Fields: cooking_skills, new_recipe_frequency, recipe_factors (JSON array),
     recipe_usage_frequency, cooking_frequency, trust_human_recipes, trust_ai_recipes,
     ai_recipe_usage, comments, attention_check_post
"""

import os
import sys

# Add the parent directory to the Python path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import init_db, DB_PATH

def recreate_database():
    """
    Recreate the database with the updated schema.
    WARNING: This will delete all existing data!
    """
    print("🗄️  DATABASE RECREATION SCRIPT")
    print("=" * 50)
    print("⚠️  WARNING: This will delete all existing survey data!")
    print("\nCurrent database schema includes:")
    print("📋 PARTICIPANTS: Prolific integration (prolific_pid, study_id, session_id)")
    print("🍽️  RECIPE EVALUATIONS: 8-question format + attention check (select '3')")
    print("📊 POST SURVEYS: Updated questions + attention check (select 'Gemini')")
    
    response = input("\nAre you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    print("\n🔄 Recreating database...")
    
    # Remove existing database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✅ Removed existing database: {DB_PATH}")
    else:
        print("ℹ️  No existing database found")
    
    # Create new database with updated schema
    init_db()
    print(f"✅ Created new database with updated schema: {DB_PATH}")
    
    print("\n🎉 Database recreation completed successfully!")
    print("\n📋 Schema Details:")
    print("   • PARTICIPANTS: Enhanced with Prolific fields")
    print("   • RECIPE_EVALUATIONS: 8-question evaluation format + attention check")
    print("   • POST_SURVEYS: Updated with checkbox recipe_factors, ai_recipe_usage + attention check")
    print("\n🚀 Ready for data collection!")

if __name__ == "__main__":
    recreate_database()