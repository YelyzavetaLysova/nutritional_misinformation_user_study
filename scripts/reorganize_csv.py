#!/usr/bin/env python3
"""
Script to reorganize the existing CSV data into a more consistent format.
This will create a new CSV file with properly ordered columns.
"""

import os
import json
import csv
import glob
from datetime import datetime

# Define the consistent order for fields
ordered_fieldnames = [
    # Participant metadata
    "participant_id", 
    "participant_date", 
    "participant_random_id",
    "start_time", 
    "completed_time", 
    "time_spent_minutes",
    "current_step", 
    "completed",
    
    # Demographics
    "demographics_age",
    "demographics_gender",
    "demographics_education",
    "demographics_cooking_frequency",
    
    # Recipe metadata
    "recipe_1_id", "recipe_1_name", "recipe_1_category",
    "recipe_2_id", "recipe_2_name", "recipe_2_category",
    "recipe_3_id", "recipe_3_name", "recipe_3_category",
    "recipe_4_id", "recipe_4_name", "recipe_4_category",
    "recipe_5_id", "recipe_5_name", "recipe_5_category",
    
    # Recipe evaluation 1
    "recipe_eval_1_recipe_id", "recipe_eval_1_recipe_name", "recipe_eval_1_recipe_category",
    "recipe_eval_1_healthiness_rating", "recipe_eval_1_tastiness_rating", 
    "recipe_eval_1_credibility_rating", "recipe_eval_1_would_make", "recipe_eval_1_comments",
    
    # Recipe evaluation 2
    "recipe_eval_2_recipe_id", "recipe_eval_2_recipe_name", "recipe_eval_2_recipe_category",
    "recipe_eval_2_healthiness_rating", "recipe_eval_2_tastiness_rating", 
    "recipe_eval_2_credibility_rating", "recipe_eval_2_would_make", "recipe_eval_2_comments",
    
    # Recipe evaluation 3
    "recipe_eval_3_recipe_id", "recipe_eval_3_recipe_name", "recipe_eval_3_recipe_category",
    "recipe_eval_3_healthiness_rating", "recipe_eval_3_tastiness_rating", 
    "recipe_eval_3_credibility_rating", "recipe_eval_3_would_make", "recipe_eval_3_comments",
    
    # Recipe evaluation 4
    "recipe_eval_4_recipe_id", "recipe_eval_4_recipe_name", "recipe_eval_4_recipe_category",
    "recipe_eval_4_healthiness_rating", "recipe_eval_4_tastiness_rating", 
    "recipe_eval_4_credibility_rating", "recipe_eval_4_would_make", "recipe_eval_4_comments",
    
    # Recipe evaluation 5
    "recipe_eval_5_recipe_id", "recipe_eval_5_recipe_name", "recipe_eval_5_recipe_category",
    "recipe_eval_5_healthiness_rating", "recipe_eval_5_tastiness_rating", 
    "recipe_eval_5_credibility_rating", "recipe_eval_5_would_make", "recipe_eval_5_comments",
    
    # Post survey
    "post_survey_trust_ai_recipes", "post_survey_trust_human_recipes",
    "post_survey_preferred_source", "post_survey_ai_knowledge", "post_survey_comments"
]

def extract_participant_info(participant_id):
    """Extract date and random ID from participant ID"""
    result = {
        "participant_id": participant_id,
        "participant_date": None,
        "participant_random_id": None
    }
    
    if participant_id.startswith('p_'):
        # Format is typically p_YYYYMMDDhhmmss_XXXX
        try:
            id_parts = participant_id.split('_')
            if len(id_parts) == 3:
                # Extract date part
                date_str = id_parts[1]
                if len(date_str) >= 8:  # Has at least YYYYMMDD format
                    result["participant_date"] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                
                # Extract random identifier
                result["participant_random_id"] = id_parts[2]
        except Exception:
            pass
    
    return result

def calculate_time_spent(start_time, completed_time):
    """Calculate time spent in the survey in minutes"""
    if not start_time or not completed_time:
        return None
    
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(completed_time)
        time_spent_seconds = (end_dt - start_dt).total_seconds()
        # Convert to minutes
        return round(time_spent_seconds / 60, 2)
    except Exception:
        return None

def main():
    # Path to responses directory
    responses_dir = "data/responses"
    json_pattern = os.path.join(responses_dir, "p_*.json")
    
    # Output CSV path
    output_csv = os.path.join(responses_dir, "reorganized_responses.csv")
    
    # Get all participant JSON files
    json_files = glob.glob(json_pattern)
    print(f"Found {len(json_files)} participant JSON files")
    
    all_responses = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                participant_data = json.load(f)
            
            # Get participant ID from filename
            filename = os.path.basename(json_file)
            participant_id = filename.replace('.json', '')
            
            # Create a flattened dict for CSV writing
            flattened_data = {}
            
            # Add participant info
            flattened_data.update(extract_participant_info(participant_id))
            
            # Add start_time if available from all_responses.csv
            start_time = None
            try:
                with open(os.path.join(responses_dir, "all_responses.csv"), 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'participant_id' in row and row['participant_id'] == participant_id and 'start_time' in row:
                            start_time = row['start_time']
                            flattened_data["start_time"] = start_time
                            break
            except (FileNotFoundError, IOError):
                # If the CSV file doesn't exist, just continue
                pass
            
            # Calculate time spent if completed
            completed_time = participant_data.get("completed_time")
            if completed_time:
                flattened_data["completed_time"] = completed_time
                
                if start_time:
                    time_spent = calculate_time_spent(start_time, completed_time)
                    if time_spent:
                        flattened_data["time_spent_minutes"] = time_spent
            
            # Flatten nested responses
            for section, responses in participant_data.items():
                if isinstance(responses, dict):
                    for key, value in responses.items():
                        flattened_data[f"{section}_{key}"] = value
                else:
                    flattened_data[section] = responses
            
            # Mark as completed if it has completed_time
            flattened_data["completed"] = "completed_time" in participant_data
            
            # Add current step based on data completeness
            if "post_survey_trust_ai_recipes" in flattened_data:
                flattened_data["current_step"] = 6  # Post survey completed
            elif "recipe_eval_5_healthiness_rating" in flattened_data:
                flattened_data["current_step"] = 5  # All recipes evaluated
            elif "recipe_eval_4_healthiness_rating" in flattened_data:
                flattened_data["current_step"] = 4  # Four recipes evaluated
            elif "recipe_eval_3_healthiness_rating" in flattened_data:
                flattened_data["current_step"] = 3  # Three recipes evaluated
            elif "recipe_eval_2_healthiness_rating" in flattened_data:
                flattened_data["current_step"] = 2  # Two recipes evaluated
            elif "recipe_eval_1_healthiness_rating" in flattened_data:
                flattened_data["current_step"] = 1  # One recipe evaluated
            else:
                flattened_data["current_step"] = 0  # Demographics only
            
            all_responses.append(flattened_data)
            
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    # Get all keys from all responses
    all_keys = set()
    for response in all_responses:
        all_keys.update(response.keys())
    
    # Update ordered_fieldnames with any missing keys
    for key in all_keys:
        if key not in ordered_fieldnames:
            ordered_fieldnames.append(key)
    
    # Write to CSV
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=ordered_fieldnames)
        writer.writeheader()
        writer.writerows(all_responses)
    
    print(f"Reorganized responses written to {output_csv}")

if __name__ == "__main__":
    main()
