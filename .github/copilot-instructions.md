<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Nutritional Misinformation Survey App

This is a FastAPI-based survey application for collecting user evaluations of recipes. The application follows a specific flow:

1. Demographics collection
2. Random selection of 5 recipes from different categories
3. Recipe evaluation (5 steps, one per recipe)
4. Post-survey questions
5. Debriefing

## Key Components

- FastAPI backend
- Jinja2 templates for frontend
- Mobile-first design with CSS
- Session management for survey flow control
- CSV data storage for responses
- Logging for error tracking

## Project Structure

- `/app/main.py`: Main application code with FastAPI routes
- `/app/templates/`: HTML templates for the survey pages
- `/app/static/css/`: CSS styling for mobile view
- `/data/`: Contains input data (recipes.csv) and survey responses
- `/logs/`: Application logs

## Coding Guidelines

- Maintain the strict survey flow (prevent step skipping)
- Ensure mobile-friendly design for all components
- Use proper logging for any errors or warnings
- Save participant responses incrementally throughout the survey
- Randomize recipe selection from different categories
