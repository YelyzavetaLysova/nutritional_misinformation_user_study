# Nutritional Misinformation User Study

A lightweight FastAPI survey application that presents recipe evaluations and collects user responses.

## Overview

This application is designed to conduct a survey about recipe perception and nutritional information. The survey follows this flow:

1. Demographics data collection
2. Evaluation of 5 randomly selected recipes (one from each category if possible)
3. Post-survey questions
4. Debriefing

## Features

- Mobile-friendly design that works on desktop browsers
- Randomization of recipes for each participant (5 recipes from different categories)
- Prevention of survey step skipping
- Data storage in CSV format
- Logging for monitoring and debugging

## Setup

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python3 -m venv venv
   ```
3. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```
4. Install dependencies:
   ```
   pip install fastapi uvicorn pandas jinja2 python-multipart
   ```

### Running the Application

Run the application with:

```
python run.py
```

The application will be available at http://localhost:8000

## Data Structure

### Input Data

Recipe data is expected in a CSV file at `data/recipes.csv` with semicolon (`;`) separators and the following columns:
- Recipe Name
- Description
- Ingredients
- Instructions
- Energy(kcal)
- Protein(g)
- Carbohydrates(g)
- Dietary Fiber(g)
- Sugar(g)
- Fat(g)
- Saturated Fat(g)
- Sodium(mg)
- Category
- (and other optional columns)

### Output Data

Survey responses are stored in two formats:
1. Individual participant JSON files in `data/responses/[participant_id].json`
2. Combined CSV file at `data/responses/all_responses.csv`

## Logging

Application logs are stored in `logs/app.log`
