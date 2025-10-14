#!/usr/bin/env python3
"""
Script to recreate the database with the updated schema including security features.
This will drop the existing database and create a new one with the latest structure.

DATABASE SCHEMA OVERVIEW:
=========================

1. PARTICIPANTS TABLE:
   - Basic participant info with Prolific integration
   - Security fields: current_step, step_completed_at, last_activity_at
   - Fields: participant_id, prolific_pid, study_id, session_id, start_time, completed_time, 
     completed, time_spent_minutes, current_step, step_completed_at, last_activity_at,
     age, gender, education

2. RECIPE_EVALUATIONS TABLE:
   - 8-question format for recipe evaluation + attention check (step 3 only)
   - Fields: completeness_rating, healthiness_rating, tastiness_rating, feasibility_rating,
     would_make, ingredients_complexity, instructions_complexity, ingredients_correctness,
     instructions_correctness, nutrition_correctness, comments, attention_check_recipe

3. POST_SURVEYS TABLE:
   - Updated post-survey questions + attention check (select 'gemini')
   - Fields: cooking_skills, new_recipe_frequency, recipe_factors (JSON array),
     recipe_usage_frequency, cooking_frequency, trust_human_recipes, trust_ai_recipes,
     ai_recipe_usage, comments, attention_check_post

SECURITY FEATURES:
==================
- Step validation (current_step tracking)
- Session timeout (last_activity_at tracking)
- Attention checks (recipe step 3 + post-survey)
- Response time validation (captured in application)
- Session manipulation detection (Prolific duplicate checking)
"""

import os
import sys

# Add the parent directory to the Python path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import init_db, DB_PATH

def recreate_database():
    """
    Recreate the database with the updated schema including security features.
    WARNING: This will delete all existing data!
    """
    print("🗄️  DATABASE RECREATION SCRIPT - WITH SECURITY FEATURES")
    print("=" * 60)
    print("⚠️  WARNING: This will delete all existing survey data!")
    print("\nUpdated database schema includes:")
    print("📋 PARTICIPANTS: Prolific integration + security tracking")
    print("   • prolific_pid, study_id, session_id")
    print("   • current_step, step_completed_at, last_activity_at")
    print("🍽️  RECIPE EVALUATIONS: 8-question format + attention check")
    print("   • Attention check on step 3 only (select '3' on scale)")
    print("📊 POST SURVEYS: Updated questions + attention check")
    print("   • Attention check: select 'gemini' from AI provider dropdown")
    print("🔒 SECURITY: Step validation, session timeout, quality monitoring")
    
    response = input("\nAre you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    print("\n🔄 Recreating database with security features...")
    
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
    print("   • PARTICIPANTS: Enhanced with Prolific fields + security tracking")
    print("   • RECIPE_EVALUATIONS: 8-question evaluation format + attention check")
    print("   • POST_SURVEYS: Updated with recipe_factors, ai_recipe_usage + attention check")
    print("   • SECURITY: Full step validation and session management")
    print("\n🚀 Ready for secure data collection!")
    print("\n🔍 Access admin dashboard at: http://localhost:8000/admin")

if __name__ == "__main__":
    recreate_database()