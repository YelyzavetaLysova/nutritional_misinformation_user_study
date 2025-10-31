"""
Database module for the nutritional misinformation survey app.
Provides functions to interact with the SQLite database.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "data/survey.db"

# Remove old database if it exists
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# Create new database with updated schema
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS participants (
    participant_id TEXT PRIMARY KEY,
    prolific_pid TEXT,
    study_id TEXT,
    session_id TEXT,
    start_time TEXT,
    completed_time TEXT,
    completed BOOLEAN,
    time_spent_minutes REAL,
    current_step INTEGER DEFAULT 0,
    step_completed_at TEXT,
    last_activity_at TEXT,
    age TEXT,
    gender TEXT,
    education TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS recipe_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id TEXT,
    eval_number INTEGER,
    recipe_id INTEGER,
    recipe_name TEXT,
    recipe_category TEXT,
    completeness_info_rating INTEGER,
    completeness_ingredients_rating INTEGER,
    completeness_steps_rating INTEGER,
    healthiness_rating INTEGER,
    tastiness_rating INTEGER,
    feasibility_rating INTEGER,
    would_make INTEGER,
    accuracy_ingredients_rating INTEGER,
    accuracy_times_rating INTEGER,
    accuracy_steps_rating INTEGER,
    accuracy_final_rating INTEGER,
    trust_try_rating INTEGER,
    trust_professional_rating INTEGER,
    trust_credible_rating INTEGER,
    comments TEXT,
    attention_check_recipe INTEGER,
    FOREIGN KEY (participant_id) REFERENCES participants (participant_id)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS post_survey (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id TEXT,
    cooking_skills INTEGER,
    new_recipe_frequency TEXT,
    recipe_factors TEXT,
    recipe_usage_frequency TEXT,
    cooking_frequency TEXT,
    trust_human_recipes INTEGER,
    trust_ai_recipes INTEGER,
    ai_recipe_usage TEXT,
    comments TEXT,
    attention_check_post TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants (participant_id)
)
''')

conn.commit()
conn.close()

def init_db():
    """
    Initialize the database and create tables if they don't exist.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS participants (
        participant_id TEXT PRIMARY KEY,
        prolific_pid TEXT,
        study_id TEXT,
        session_id TEXT,
        start_time TEXT,
        completed_time TEXT,
        completed BOOLEAN,
        time_spent_minutes REAL,
        current_step INTEGER DEFAULT 0,
        step_completed_at TEXT,
        last_activity_at TEXT,
        age TEXT,
        gender TEXT,
        education TEXT
    );

    CREATE TABLE IF NOT EXISTS recipe_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        participant_id TEXT,
        eval_number INTEGER,
        recipe_id INTEGER,
        recipe_name TEXT,
        recipe_category TEXT,
        completeness_info_rating INTEGER,
        completeness_ingredients_rating INTEGER,
        completeness_steps_rating INTEGER,
        healthiness_rating INTEGER,
        tastiness_rating INTEGER,
        feasibility_rating INTEGER,
        would_make INTEGER,
        accuracy_ingredients_rating INTEGER,
        accuracy_times_rating INTEGER,
        accuracy_steps_rating INTEGER,
        accuracy_final_rating INTEGER,
        trust_try_rating INTEGER,
        trust_professional_rating INTEGER,
        trust_credible_rating INTEGER,
        comments TEXT,
        attention_check_recipe INTEGER,
        FOREIGN KEY (participant_id) REFERENCES participants (participant_id)
    );

    CREATE TABLE IF NOT EXISTS post_survey (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        participant_id TEXT,
        cooking_skills INTEGER,
        new_recipe_frequency TEXT,
        recipe_factors TEXT,
        recipe_usage_frequency TEXT,
        cooking_frequency TEXT,
        trust_human_recipes INTEGER,
        trust_ai_recipes INTEGER,
        ai_recipe_usage TEXT,
        comments TEXT,
        attention_check_post TEXT,
        FOREIGN KEY (participant_id) REFERENCES participants (participant_id)
    );
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def save_participant(participant_data: Dict[str, Any]):
    """
    Save or update a participant and their responses to the database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        participant_id = participant_data.get("id")
        
        # Check if participant already exists
        cursor.execute("SELECT participant_id FROM participants WHERE participant_id = ?", 
                      (participant_id,))
        existing = cursor.fetchone()
        
        # Calculate time spent if available
        time_spent_minutes = None
        start_time = participant_data.get("start_time")
        completed_time = participant_data.get("responses", {}).get("completed_time")
        
        if start_time and completed_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(completed_time)
                time_spent_seconds = (end_dt - start_dt).total_seconds()
                time_spent_minutes = round(time_spent_seconds / 60, 2)
            except Exception as e:
                logger.warning(f"Could not calculate time spent: {e}")
        
        # Get demographics and Prolific info
        demographics = participant_data.get("responses", {}).get("demographics", {})
        prolific_info = participant_data.get("responses", {}).get("prolific_info", {})
        
        # Debug logging for Prolific info
        logger.info(f"Saving participant {participant_id} with Prolific info: {prolific_info}")
        
        # Insert or update participant data
        if existing:
            cursor.execute("""
            UPDATE participants SET 
                prolific_pid = ?,
                study_id = ?,
                session_id = ?,
                start_time = ?,
                completed_time = ?,
                completed = ?,
                time_spent_minutes = ?,
                current_step = ?,
                step_completed_at = ?,
                last_activity_at = ?,
                age = ?,
                gender = ?,
                education = ?
            WHERE participant_id = ?
            """, (
                prolific_info.get("prolific_pid"),
                prolific_info.get("study_id"),
                prolific_info.get("session_id"),
                start_time,
                completed_time,
                participant_data.get("completed", False),
                time_spent_minutes,
                participant_data.get("current_step", 0),
                participant_data.get("step_completed_at"),
                datetime.now().isoformat(),
                demographics.get("age"),
                demographics.get("gender"),
                demographics.get("education"),
                participant_id
            ))
            logger.info(f"Updated participant {participant_id} in database")
        else:
            cursor.execute("""
            INSERT INTO participants 
            (participant_id, prolific_pid, study_id, session_id, start_time, completed_time, completed, time_spent_minutes,
             current_step, step_completed_at, last_activity_at, age, gender, education)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                participant_id,
                prolific_info.get("prolific_pid"),
                prolific_info.get("study_id"),
                prolific_info.get("session_id"),
                start_time,
                completed_time,
                participant_data.get("completed", False),
                time_spent_minutes,
                participant_data.get("current_step", 0),
                participant_data.get("step_completed_at"),
                datetime.now().isoformat(),
                demographics.get("age"),
                demographics.get("gender"),
                demographics.get("education")
            ))
            logger.info(f"Added participant {participant_id} to database")
        
        # Save demographics (now part of participants)
        cursor.execute("""
        UPDATE participants SET age = ?, gender = ?, education = ? WHERE participant_id = ?
        """, (
            demographics.get("age"),
            demographics.get("gender"),
            demographics.get("education"),
            participant_id
        ))
        
        # Save recipe evaluations
        for i in range(1, 6):
            eval_key = f"recipe_eval_{i}"
            if eval_key in participant_data.get("responses", {}):
                eval_data = participant_data["responses"][eval_key]
                
                # Check if evaluation already exists
                cursor.execute("""
                SELECT id FROM recipe_evaluations 
                WHERE participant_id = ? AND eval_number = ?
                """, (participant_id, i))
                
                existing = cursor.fetchone()
                
                # Handle backward compatibility for existing data
                # Map old field names to new ones if they exist
                
                if existing:
                    cursor.execute("""
                    UPDATE recipe_evaluations SET
                        recipe_id = ?,
                        recipe_name = ?,
                        recipe_category = ?,
                        completeness_info_rating = ?,
                        completeness_ingredients_rating = ?,
                        completeness_steps_rating = ?,
                        healthiness_rating = ?,
                        tastiness_rating = ?,
                        feasibility_rating = ?,
                        would_make = ?,
                        accuracy_ingredients_rating = ?,
                        accuracy_times_rating = ?,
                        accuracy_steps_rating = ?,
                        accuracy_final_rating = ?,
                        trust_try_rating = ?,
                        trust_professional_rating = ?,
                        trust_credible_rating = ?,
                        comments = ?,
                        attention_check_recipe = ?
                    WHERE participant_id = ? AND eval_number = ?
                    """, (
                        eval_data.get("recipe_id"),
                        eval_data.get("recipe_name"),
                        eval_data.get("recipe_category"),
                        eval_data.get("completeness_info_rating"),
                        eval_data.get("completeness_ingredients_rating"),
                        eval_data.get("completeness_steps_rating"),
                        eval_data.get("healthiness_rating"),
                        eval_data.get("tastiness_rating"),
                        eval_data.get("feasibility_rating"),
                        eval_data.get("would_make"),
                        eval_data.get("accuracy_ingredients_rating"),
                        eval_data.get("accuracy_times_rating"),
                        eval_data.get("accuracy_steps_rating"),
                        eval_data.get("accuracy_final_rating"),
                        eval_data.get("trust_try_rating"),
                        eval_data.get("trust_professional_rating"),
                        eval_data.get("trust_credible_rating"),
                        eval_data.get("comments", ""),
                        eval_data.get("attention_check_recipe"),
                        participant_id,
                        i
                    ))
                else:
                    cursor.execute("""
                    INSERT INTO recipe_evaluations
                    (participant_id, eval_number, recipe_id, recipe_name, recipe_category,
                     completeness_info_rating, completeness_ingredients_rating, completeness_steps_rating,
                     healthiness_rating, tastiness_rating, feasibility_rating, would_make,
                     accuracy_ingredients_rating, accuracy_times_rating, accuracy_steps_rating, accuracy_final_rating,
                     trust_try_rating, trust_professional_rating, trust_credible_rating,
                     comments, attention_check_recipe)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        participant_id,
                        i,
                        eval_data.get("recipe_id"),
                        eval_data.get("recipe_name"),
                        eval_data.get("recipe_category"),
                        eval_data.get("completeness_info_rating"),
                        eval_data.get("completeness_ingredients_rating"),
                        eval_data.get("completeness_steps_rating"),
                        eval_data.get("healthiness_rating"),
                        eval_data.get("tastiness_rating"),
                        eval_data.get("feasibility_rating"),
                        eval_data.get("would_make"),
                        eval_data.get("accuracy_ingredients_rating"),
                        eval_data.get("accuracy_times_rating"),
                        eval_data.get("accuracy_steps_rating"),
                        eval_data.get("accuracy_final_rating"),
                        eval_data.get("trust_try_rating"),
                        eval_data.get("trust_professional_rating"),
                        eval_data.get("trust_credible_rating"),
                        eval_data.get("comments", ""),
                        eval_data.get("attention_check_recipe")
                    ))
        
        # Save post survey data
        if "post_survey" in participant_data.get("responses", {}):
            post_data = participant_data["responses"]["post_survey"]
            
            # Check if post survey already exists
            cursor.execute("""
            SELECT id FROM post_survey WHERE participant_id = ?
            """, (participant_id,))
            
            existing = cursor.fetchone()
            
            # Handle recipe factors as JSON array
            recipe_factors = post_data.get("recipe_factors", [])
            if isinstance(recipe_factors, list):
                recipe_factors_json = json.dumps(recipe_factors)
            else:
                recipe_factors_json = json.dumps([recipe_factors]) if recipe_factors else json.dumps([])
            
            if existing:
                cursor.execute("""
                UPDATE post_survey SET
                    cooking_skills = ?,
                    new_recipe_frequency = ?,
                    recipe_factors = ?,
                    recipe_usage_frequency = ?,
                    cooking_frequency = ?,
                    trust_human_recipes = ?,
                    trust_ai_recipes = ?,
                    ai_recipe_usage = ?,
                    comments = ?,
                    attention_check_post = ?
                WHERE participant_id = ?
                """, (
                    post_data.get("cooking_skills"),
                    post_data.get("new_recipe_frequency"),
                    recipe_factors_json,
                    post_data.get("recipe_usage_frequency"),
                    post_data.get("cooking_frequency"),
                    post_data.get("trust_human_recipes"),
                    post_data.get("trust_ai_recipes"),
                    post_data.get("ai_recipe_usage"),
                    post_data.get("comments", ""),
                    post_data.get("attention_check_post"),
                    participant_id
                ))
            else:
                cursor.execute("""
                INSERT INTO post_survey
                (participant_id, cooking_skills, new_recipe_frequency, recipe_factors,
                 recipe_usage_frequency, cooking_frequency, trust_human_recipes, trust_ai_recipes, ai_recipe_usage, comments, attention_check_post)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    participant_id,
                    post_data.get("cooking_skills"),
                    post_data.get("new_recipe_frequency"),
                    recipe_factors_json,
                    post_data.get("recipe_usage_frequency"),
                    post_data.get("cooking_frequency"),
                    post_data.get("trust_human_recipes"),
                    post_data.get("trust_ai_recipes"),
                    post_data.get("ai_recipe_usage"),
                    post_data.get("comments", ""),
                    post_data.get("attention_check_post")
                ))
        
        conn.commit()
        logger.info(f"Successfully saved all data for participant {participant_id}")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving participant data: {e}")
        return False
    finally:
        conn.close()


def import_existing_data():
    """
    Import existing data from JSON files into the database.
    """
    import glob
    import json
    
    # Find all participant JSON files
    json_files = glob.glob("data/responses/p_*.json")
    logger.info(f"Found {len(json_files)} participant JSON files")
    
    imported_count = 0
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            participant_id = os.path.basename(json_file).replace('.json', '')
            
            # Create a participant data structure that matches what our save function expects
            participant_data = {
                "id": participant_id,
                "start_time": data.get("start_time"),
                "completed": "completed_time" in data,
                "responses": data,
                "selected_recipes": []
            }
            
            # Extract recipe IDs if available
            for i in range(1, 6):
                eval_key = f"recipe_eval_{i}"
                if eval_key in data and "recipe_id" in data[eval_key]:
                    participant_data["selected_recipes"].append(data[eval_key]["recipe_id"])
            
            # Save to database
            if save_participant(participant_data):
                imported_count += 1
                
        except Exception as e:
            logger.error(f"Error importing {json_file}: {e}")
    
    logger.info(f"Successfully imported {imported_count} participants to the database")
    return imported_count


def get_participant_data(participant_id: str) -> Optional[Dict]:
    """
    Retrieve a participant's data from the database.
    Returns None if participant doesn't exist.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    try:
        # Get participant data
        cursor.execute("""
        SELECT * FROM participants WHERE participant_id = ?
        """, (participant_id,))
        
        participant_row = cursor.fetchone()
        if not participant_row:
            return None
        
        # Convert row to dict
        participant = dict(participant_row)
        
        # Get recipe evaluations
        cursor.execute("""
        SELECT * FROM recipe_evaluations 
        WHERE participant_id = ? 
        ORDER BY eval_number
        """, (participant_id,))
        
        evaluations = [dict(row) for row in cursor.fetchall()]
        
        # Get post survey
        cursor.execute("""
        SELECT * FROM post_survey 
        WHERE participant_id = ?
        """, (participant_id,))
        
        post_survey = cursor.fetchone()
        if post_survey:
            post_survey = dict(post_survey)
        
        # Combine all data
        result = {
            "participant": participant,
            "recipe_evaluations": evaluations,
            "post_survey": post_survey
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving participant data: {e}")
        return None
    finally:
        conn.close()


def export_to_csv():
    """
    Export all data from the database to CSV files for compatibility
    with the existing analysis scripts.
    """
    import csv
    import pandas as pd
    import os
    
    os.makedirs("data/normalized", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Export participants
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM participants")
        participants = [dict(row) for row in cursor.fetchall()]
        
        if participants:
            df = pd.DataFrame(participants)
            df.to_csv("data/normalized/participants.csv", index=False)
            logger.info(f"Exported {len(participants)} participants to CSV")
        
        # Export recipe evaluations
        cursor.execute("SELECT * FROM recipe_evaluations")
        evaluations = [dict(row) for row in cursor.fetchall()]
        
        if evaluations:
            df = pd.DataFrame(evaluations)
            df.to_csv("data/normalized/recipe_evaluations.csv", index=False)
            logger.info(f"Exported {len(evaluations)} recipe evaluations to CSV")
        
        # Export post surveys
        cursor.execute("SELECT * FROM post_survey")
        surveys = [dict(row) for row in cursor.fetchall()]
        
        if surveys:
            df = pd.DataFrame(surveys)
            df.to_csv("data/normalized/post_survey.csv", index=False)
            logger.info(f"Exported {len(surveys)} post surveys to CSV")
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting data to CSV: {e}")
        return False
    finally:
        conn.close()


def check_prolific_duplicate(prolific_pid: str) -> List[Dict]:
    """
    Check for duplicate Prolific participants.
    Returns list of participant records with same prolific_pid.
    """
    if not prolific_pid:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        SELECT participant_id, start_time, completed, current_step, last_activity_at
        FROM participants 
        WHERE prolific_pid = ? 
        ORDER BY start_time
        """, (prolific_pid,))
        
        results = [dict(row) for row in cursor.fetchall()]
        return results
        
    except Exception as e:
        logger.error(f"Error checking Prolific duplicates: {e}")
        return []
    finally:
        conn.close()

def get_quality_metrics() -> Dict[str, any]:
    """
    Get data quality metrics from the database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    metrics = {
        "total_participants": 0,
        "completed_participants": 0,
        "prolific_participants": 0,
        "attention_check_failures": 0,
        "duplicate_prolific_ids": 0,
        "fast_responses": 0,
        "slow_responses": 0
    }
    
    try:
        # Total participants
        cursor.execute("SELECT COUNT(*) FROM participants")
        metrics["total_participants"] = cursor.fetchone()[0]
        
        # Completed participants
        cursor.execute("SELECT COUNT(*) FROM participants WHERE completed = 1")
        metrics["completed_participants"] = cursor.fetchone()[0]
        
        # Prolific participants
        cursor.execute("SELECT COUNT(*) FROM participants WHERE prolific_pid IS NOT NULL")
        metrics["prolific_participants"] = cursor.fetchone()[0]
        
        # Attention check failures (recipe eval step 3)
        cursor.execute("SELECT COUNT(*) FROM recipe_evaluations WHERE attention_check_recipe IS NOT NULL AND attention_check_recipe != 3")
        recipe_failures = cursor.fetchone()[0]
        
        # Attention check failures (post survey)
        cursor.execute("SELECT COUNT(*) FROM post_survey WHERE attention_check_post IS NOT NULL AND attention_check_post != 'gemini'")
        post_failures = cursor.fetchone()[0]
        
        metrics["attention_check_failures"] = recipe_failures + post_failures
        
        # Duplicate Prolific IDs
        cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT prolific_pid FROM participants 
            WHERE prolific_pid IS NOT NULL 
            GROUP BY prolific_pid 
            HAVING COUNT(*) > 1
        )
        """)
        metrics["duplicate_prolific_ids"] = cursor.fetchone()[0]
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        return metrics
    finally:
        conn.close()

def get_participants_with_quality_flags() -> List[Dict]:
    """
    Get all participants with their quality assessment flags.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        SELECT p.participant_id, p.prolific_pid, p.completed, p.time_spent_minutes,
               p.start_time, p.completed_time,
               -- Check for attention check failures
               (SELECT COUNT(*) FROM recipe_evaluations re 
                WHERE re.participant_id = p.participant_id 
                AND re.attention_check_recipe IS NOT NULL 
                AND re.attention_check_recipe != 3) as recipe_attention_failures,
               (SELECT COUNT(*) FROM post_survey ps 
                WHERE ps.participant_id = p.participant_id 
                AND ps.attention_check_post IS NOT NULL 
                AND ps.attention_check_post != 'gemini') as post_attention_failures,
               -- Get response time info (would need additional processing)
               p.last_activity_at
        FROM participants p
        ORDER BY p.start_time DESC
        """)
        
        participants = []
        for row in cursor.fetchall():
            participant = dict(row)
            
            # Add quality flags
            participant["attention_check_passed"] = (
                participant["recipe_attention_failures"] == 0 and 
                participant["post_attention_failures"] == 0
            )
            
            # Check for duplicate Prolific IDs if this is a Prolific participant
            if participant["prolific_pid"]:
                duplicates = check_prolific_duplicate(participant["prolific_pid"])
                participant["has_prolific_duplicates"] = len(duplicates) > 1
                participant["prolific_duplicate_count"] = len(duplicates)
            else:
                participant["has_prolific_duplicates"] = False
                participant["prolific_duplicate_count"] = 0
            
            participants.append(participant)
        
        return participants
        
    except Exception as e:
        logger.error(f"Error getting participants with quality flags: {e}")
        return []
    finally:
        conn.close()
