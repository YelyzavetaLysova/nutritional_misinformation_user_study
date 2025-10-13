# Prolific Configuration
# This file contains configuration settings for Prolific integration

import os

# Prolific completion URL - REPLACE WITH YOUR ACTUAL COMPLETION CODE
# You'll get this from Prolific when you create your study
PROLIFIC_COMPLETION_URL = os.getenv(
    "PROLIFIC_COMPLETION_URL", 
    "https://app.prolific.co/submissions/complete?cc=C12345AB"  # Replace with your actual completion code from Prolific
)

# Study settings
STUDY_SETTINGS = {
    "estimated_completion_time": 10,  # minutes
    "reward_amount": 1.67,  # GBP (adjust based on your budget)
    "participant_requirements": {
        "age_min": 18,
        "age_max": 65,
        "languages": ["en"],
        "countries": ["GB", "US", "CA", "AU"]  # Adjust as needed
    }
}

# Validation settings
PROLIFIC_VALIDATION = {
    "required_parameters": ["PROLIFIC_PID", "STUDY_ID", "SESSION_ID"],
    "validate_on_entry": True
}
