import os
import csv
import json
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Set

import pandas as pd
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

# Import the database module
from app.db import save_participant, get_participant_data, init_db

# Ensure directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("data/responses", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Recipe Feasibility Study")
app.add_middleware(SessionMiddleware, secret_key="recipe_feasibility_survey_secret_key")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Initialize database
init_db()

# Load recipe data
try:
    recipes_df = pd.read_csv("data/recipes.csv", sep=";")
    logger.info(f"Loaded {len(recipes_df)} recipes from CSV file")
    
    # Clean up recipe categories (trim whitespace)
    # recipes_df["Category"] = recipes_df["Category"].str.strip()
    
    # Convert recipe categories to a set for easier lookup
    recipe_categories = set(recipes_df["Category"].unique())
    
    # Log the categories and counts
    category_counts = recipes_df["Category"].value_counts().to_dict()
    logger.info(f"Found {len(recipe_categories)} recipe categories: {recipe_categories}")
    logger.info(f"Recipe counts by category: {category_counts}")
    
    # Check for similar categories that might just be whitespace differences
    normalized_categories = {}
    for cat in recipe_categories:
        normalized = cat.strip().lower()
        if normalized not in normalized_categories:
            normalized_categories[normalized] = []
        normalized_categories[normalized].append(cat)
    
    # Log categories that might be duplicates
    for norm_cat, variants in normalized_categories.items():
        if len(variants) > 1:
            logger.warning(f"Possible duplicate categories found: {variants} (normalized to '{norm_cat}')")
    
except Exception as e:
    logger.error(f"Failed to load recipe data: {e}")
    recipes_df = None
    recipe_categories = set()

# Constants
NUM_RECIPES_PER_PARTICIPANT = 5
REQUIRED_STEPS = ["demographics", "recipe_eval_1", "recipe_eval_2", "recipe_eval_3", "recipe_eval_4", "recipe_eval_5", "post_survey", "debriefing"]


class Participant(BaseModel):
    id: str
    selected_recipes: List[int]
    current_step: int = 0
    responses: Dict = {}
    completed: bool = False
    start_time: Optional[str] = None


# In-memory participant data store (replace with a database in production)
participants = {}


def get_participant_from_session(request: Request) -> Optional[Participant]:
    """Get participant data from session or create a new participant."""
    if "participant_id" not in request.session:
        return None
    
    participant_id = request.session.get("participant_id")
    
    # First try to get from in-memory cache
    if participant_id in participants:
        return participants[participant_id]
    
    # If not in memory, try to get from database
    from app.db import get_participant_data
    db_data = get_participant_data(participant_id)
    if db_data:
        # Convert database data to Participant model
        participant_row = db_data.get("participant", {})
        evaluations = db_data.get("recipe_evaluations", [])
        post_survey = db_data.get("post_survey", {})
        
        # Get selected recipes from evaluations
        selected_recipes = []
        responses = {}
        
        # Add demographics if available
        responses["demographics"] = {
            "age": participant_row.get("age"),
            "gender": participant_row.get("gender"),
            "education": participant_row.get("education"),
            "nationality": participant_row.get("nationality")
        }
        
        # Add evaluations to responses
        for eval_data in evaluations:
            eval_number = eval_data.get("eval_number")
            responses[f"recipe_eval_{eval_number}"] = {
                "recipe_id": eval_data.get("recipe_id"),
                "recipe_name": eval_data.get("recipe_name"),
                "recipe_category": eval_data.get("recipe_category"),
                "clarity_rating": eval_data.get("clarity_rating"),
                "tastiness_rating": eval_data.get("tastiness_rating"),
                "completeness_rating": eval_data.get("completeness_rating"),
                "correctness_rating": eval_data.get("correctness_rating"),
                "ingredients_correctness": eval_data.get("ingredients_correctness"),
                "instructions_correctness": eval_data.get("instructions_correctness"),
                "nutrition_correctness": eval_data.get("nutrition_correctness"),
                "feasibility_rating": eval_data.get("feasibility_rating"),
                "quality_rating": eval_data.get("quality_rating"),
                "would_make": eval_data.get("would_make"),
                "comments": eval_data.get("comments", "")
            }
            
            # Track recipe IDs
            if eval_data.get("recipe_id") is not None:
                selected_recipes.append(eval_data.get("recipe_id"))
        
        # Add post survey if available
        if post_survey:
            responses["post_survey"] = {
                "cooking_skills": post_survey.get("cooking_skills"),
                "new_recipe_frequency": post_survey.get("new_recipe_frequency"),
                "preferred_source": post_survey.get("preferred_source"),
                "cooking_frequency": post_survey.get("cooking_frequency"),
                "trust_human_recipes": post_survey.get("trust_human_recipes"),
                "trust_ai_recipes": post_survey.get("trust_ai_recipes"),
                "ai_usage": post_survey.get("ai_usage"),
                "comments": post_survey.get("comments", "")
            }
        
        # Add completion time if available
        if participant_row.get("completed_time"):
            responses["completed_time"] = participant_row.get("completed_time")
        
        # Create and cache the participant
        participant = Participant(
            id=participant_id,
            selected_recipes=selected_recipes if selected_recipes else [],
            current_step=participant_row.get("current_step", 0),
            responses=responses,
            completed=bool(participant_row.get("completed", False)),
            start_time=participant_row.get("start_time")
        )
        
        # Cache in memory for faster subsequent access
        participants[participant_id] = participant
        return participant
        
    return None


def create_new_participant() -> Participant:
    """Create a new participant with randomly selected recipes."""
    participant_id = f"p_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
    
    # Select 5 random recipes from different categories
    selected_recipes = []
    
    # Clean and normalize category names (remove trailing spaces)
    normalized_categories = {}
    for category in recipe_categories:
        normalized_cat = category.strip().lower()
        if normalized_cat not in normalized_categories:
            normalized_categories[normalized_cat] = []
        normalized_categories[normalized_cat].append(category)
    
    # Get the set of normalized category names
    unique_categories = list(normalized_categories.keys())
    
    # Ensure we have at least 5 unique categories
    if len(unique_categories) < NUM_RECIPES_PER_PARTICIPANT:
        logger.warning(f"Only {len(unique_categories)} unique categories available. Some recipes may be from similar categories.")
        
    # Shuffle categories for random selection
    random.shuffle(unique_categories)
    
    # Select 5 categories (or as many as available if less than 5)
    selected_categories = unique_categories[:min(NUM_RECIPES_PER_PARTICIPANT, len(unique_categories))]
    
    logger.info(f"Selected categories: {selected_categories}")
    
    # Select one recipe from each of the selected categories
    for i, normalized_cat in enumerate(selected_categories):
        # Get all original category names that map to this normalized category
        original_categories = normalized_categories[normalized_cat]
        
        # Create a mask for recipes in any of the matching categories
        category_mask = recipes_df["Category"].apply(lambda x: x.strip().lower() == normalized_cat)
        category_recipes = recipes_df[category_mask]
        
        if not category_recipes.empty:
            recipe_index = random.choice(category_recipes.index.tolist())
            selected_recipes.append(recipe_index)
            logger.info(f"Selected recipe {recipe_index} from category '{normalized_cat}'")
    
    # If we still don't have enough recipes (unlikely but possible if some categories have no recipes)
    remaining_needed = NUM_RECIPES_PER_PARTICIPANT - len(selected_recipes)
    if remaining_needed > 0:
        logger.warning(f"Not enough categories with recipes. Filling with {remaining_needed} random recipes.")
        attempts = 0
        
        # Try to find recipes from unused categories first
        unused_categories = [cat for cat in unique_categories if cat not in selected_categories]
        
        for normalized_cat in unused_categories:
            if len(selected_recipes) >= NUM_RECIPES_PER_PARTICIPANT:
                break
                
            category_mask = recipes_df["Category"].apply(lambda x: x.strip().lower() == normalized_cat)
            category_recipes = recipes_df[category_mask]
            
            if not category_recipes.empty:
                recipe_index = random.choice(category_recipes.index.tolist())
                if recipe_index not in selected_recipes:
                    selected_recipes.append(recipe_index)
                    logger.info(f"Added recipe {recipe_index} from unused category '{normalized_cat}'")
        
        # If still not enough, add random recipes
        while len(selected_recipes) < NUM_RECIPES_PER_PARTICIPANT and attempts < 100:
            attempts += 1
            random_index = random.choice(recipes_df.index.tolist())
            if random_index not in selected_recipes:
                selected_recipes.append(random_index)
                logger.info(f"Added random recipe {random_index}")
    
    # Shuffle the selected recipes to randomize their order in the survey
    random.shuffle(selected_recipes)
    
    # Create and store the participant
    participant = Participant(
        id=participant_id,
        selected_recipes=selected_recipes,
        start_time=datetime.now().isoformat()
    )
    
    participants[participant_id] = participant
    logger.info(f"Created new participant {participant_id} with recipes {selected_recipes}")
    
    return participant


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Homepage with study information and consent form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/start")
async def start_survey(request: Request):
    """Initialize a new participant session."""
    participant = create_new_participant()
    request.session["participant_id"] = participant.id
    logger.info(f"Starting survey with participant {participant.id}")
    return RedirectResponse(url="/demographics", status_code=303)


@app.get("/demographics", response_class=HTMLResponse)
async def demographics_form(request: Request, participant: Participant = Depends(get_participant_from_session)):
    """Demographics data collection form."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    if participant.current_step > 0:
        return RedirectResponse(url=f"/{REQUIRED_STEPS[participant.current_step]}", status_code=303)
    
    return templates.TemplateResponse("demographics.html", {"request": request})


@app.post("/demographics")
async def submit_demographics(
    request: Request,
    age: str = Form(...),
    gender: str = Form(...),
    education: str = Form(...),
    nationality: str = Form(...),
    participant: Participant = Depends(get_participant_from_session)
):
    """Process demographics form submission."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Store demographics data
    participant.responses["demographics"] = {
        "age": age,
        "gender": gender,
        "education": education,
        "nationality": nationality
    }
    
    # Update participant progress
    participant.current_step = 1
    
    # Save responses to CSV
    save_participant_responses(participant)
    
    logger.info(f"Participant {participant.id} completed demographics")
    
    # Redirect to first recipe evaluation
    return RedirectResponse(url="/recipe_eval_1", status_code=303)


@app.get("/recipe_eval_{step_id}", response_class=HTMLResponse)
async def recipe_evaluation(request: Request, step_id: int, participant: Participant = Depends(get_participant_from_session)):
    """Show recipe for evaluation."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Prevent skipping steps
    if step_id > participant.current_step:
        return RedirectResponse(url=f"/{REQUIRED_STEPS[participant.current_step]}", status_code=303)
    
    if step_id < 1 or step_id > NUM_RECIPES_PER_PARTICIPANT:
        raise HTTPException(status_code=404, detail="Invalid step")
    
    # Get recipe data
    recipe_index = participant.selected_recipes[step_id - 1]
    recipe = recipes_df.iloc[recipe_index].to_dict()
    
    return templates.TemplateResponse(
        "recipe_evaluation.html", 
        {
            "request": request, 
            "recipe": recipe, 
            "step": step_id,
            "total_steps": NUM_RECIPES_PER_PARTICIPANT
        }
    )


@app.post("/recipe_eval_{step_id}")
async def submit_recipe_evaluation(
    request: Request,
    step_id: int,
    recipe_name: str = Form(...),
    clarity_rating: int = Form(...),
    tastiness_rating: int = Form(...),
    completeness_rating: int = Form(...),
    correctness_rating: int = Form(...),
    ingredients_correctness: int = Form(...),
    instructions_correctness: int = Form(...),
    nutrition_correctness: int = Form(...),
    feasibility_rating: int = Form(...),
    quality_rating: int = Form(...),
    would_make: int = Form(...),
    comments: str = Form(None),
    participant: Participant = Depends(get_participant_from_session)
):
    """Process recipe evaluation submission."""
    # Log form data for debugging
    form_data = await request.form()
    logger.info(f"Recipe evaluation form submission data for step {step_id}: {dict(form_data)}")
    """Process recipe evaluation submission."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    if step_id < 1 or step_id > NUM_RECIPES_PER_PARTICIPANT:
        raise HTTPException(status_code=404, detail="Invalid step")
    
    # Store evaluation data
    recipe_index = participant.selected_recipes[step_id - 1]
    recipe = recipes_df.iloc[recipe_index]
    
    participant.responses[f"recipe_eval_{step_id}"] = {
        "recipe_id": recipe_index,
        "recipe_name": recipe_name,
        "recipe_category": recipe["Category"],
        "clarity_rating": clarity_rating,
        "tastiness_rating": tastiness_rating,
        "completeness_rating": completeness_rating,
        "correctness_rating": correctness_rating,
        "ingredients_correctness": ingredients_correctness,
        "instructions_correctness": instructions_correctness,
        "nutrition_correctness": nutrition_correctness,
        "feasibility_rating": feasibility_rating,
        "quality_rating": quality_rating,
        "would_make": would_make,
        "comments": comments or ""
    }
    
    # Update participant progress
    if step_id >= participant.current_step:
        participant.current_step = step_id + 1
    
    # Save responses to CSV
    save_participant_responses(participant)
    
    logger.info(f"Participant {participant.id} completed recipe evaluation {step_id}")
    
    # Determine next step
    if step_id < NUM_RECIPES_PER_PARTICIPANT:
        return RedirectResponse(url=f"/recipe_eval_{step_id + 1}", status_code=303)
    else:
        return RedirectResponse(url="/post_survey", status_code=303)


@app.get("/post_survey", response_class=HTMLResponse)
async def post_survey_form(request: Request, participant: Participant = Depends(get_participant_from_session)):
    """Post-survey questions."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Prevent skipping steps
    if participant.current_step < NUM_RECIPES_PER_PARTICIPANT:
        return RedirectResponse(url=f"/{REQUIRED_STEPS[participant.current_step]}", status_code=303)
    
    return templates.TemplateResponse("post_survey.html", {"request": request})


@app.post("/post_survey")
async def submit_post_survey(
    request: Request,
    cooking_skills: int = Form(...),
    new_recipe_frequency: str = Form(...),
    preferred_source: str = Form(...),
    cooking_frequency: str = Form(...),
    trust_human_recipes: int = Form(...),
    trust_ai_recipes: int = Form(...),
    ai_usage: str = Form(...),
    comments: str = Form(None),
    participant: Participant = Depends(get_participant_from_session)
):
    """Process post-survey submission."""
    # Log form data for debugging
    form_data = await request.form()
    logger.info(f"Post-survey form submission data: {dict(form_data)}")
    
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Store post-survey data
    participant.responses["post_survey"] = {
        "cooking_skills": cooking_skills,
        "new_recipe_frequency": new_recipe_frequency,
        "preferred_source": preferred_source,
        "cooking_frequency": cooking_frequency,
        "trust_human_recipes": trust_human_recipes,
        "trust_ai_recipes": trust_ai_recipes,
        "ai_usage": ai_usage,
        "comments": comments or ""
    }
    
    # Update participant progress
    participant.current_step = NUM_RECIPES_PER_PARTICIPANT + 1
    
    # Save responses to CSV
    save_participant_responses(participant)
    
    logger.info(f"Participant {participant.id} completed post-survey")
    
    # Redirect to debriefing
    return RedirectResponse(url="/debriefing", status_code=303)


@app.get("/debriefing", response_class=HTMLResponse)
async def debriefing(request: Request, participant: Participant = Depends(get_participant_from_session)):
    """Show debriefing information."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Prevent skipping steps
    if participant.current_step < NUM_RECIPES_PER_PARTICIPANT + 1:
        return RedirectResponse(url=f"/{REQUIRED_STEPS[participant.current_step]}", status_code=303)
    
    # Mark participant as completed
    participant.completed = True
    participant.responses["completed_time"] = datetime.now().isoformat()
    
    # Save final responses
    save_participant_responses(participant)
    
    logger.info(f"Participant {participant.id} completed the study")
    
    return templates.TemplateResponse("debriefing.html", {"request": request})


def save_participant_responses(participant: Participant):
    """Save participant responses to both JSON file and database.
    Saves each step of the survey process for each participant.
    """
    try:
        # Ensure the responses directory exists
        os.makedirs("data/responses", exist_ok=True)
        
        # Create a flattened dict for CSV writing (for backwards compatibility)
        flattened_data = {}
        
        # Add participant metadata
        flattened_data["participant_id"] = participant.id
        flattened_data["start_time"] = participant.start_time
        flattened_data["current_step"] = participant.current_step
        flattened_data["completed"] = participant.completed
        
        # Calculate time spent in survey if completed
        completed_time = participant.responses.get("completed_time")
        if participant.start_time and completed_time:
            try:
                start_dt = datetime.fromisoformat(participant.start_time)
                end_dt = datetime.fromisoformat(completed_time)
                time_spent_seconds = (end_dt - start_dt).total_seconds()
                # Convert to minutes for better readability
                time_spent_minutes = time_spent_seconds / 60
                flattened_data["time_spent_minutes"] = round(time_spent_minutes, 2)
            except Exception as e:
                logger.warning(f"Could not calculate time spent: {e}")
        
        # Add selected recipe IDs
        for i, recipe_idx in enumerate(participant.selected_recipes):
            recipe = recipes_df.iloc[recipe_idx]
            flattened_data[f"recipe_{i+1}_id"] = recipe_idx
            flattened_data[f"recipe_{i+1}_name"] = recipe["Recipe Name"]
            flattened_data[f"recipe_{i+1}_category"] = recipe["Category"]
        
        # Extract participant ID components for easier filtering/analysis
        if participant.id.startswith('p_'):
            # Format is typically p_YYYYMMDDhhmmss_XXXX
            try:
                id_parts = participant.id.split('_')
                if len(id_parts) == 3:
                    # Extract date part
                    date_str = id_parts[1]
                    if len(date_str) >= 8:  # Has at least YYYYMMDD format
                        flattened_data["participant_date"] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    
                    # Extract random identifier
                    flattened_data["participant_random_id"] = id_parts[2]
            except Exception as e:
                logger.warning(f"Could not parse participant ID components: {e}")
        
        # Flatten nested responses
        for section, responses in participant.responses.items():
            if isinstance(responses, dict):
                for key, value in responses.items():
                    flattened_data[f"{section}_{key}"] = value
            else:
                flattened_data[section] = responses
        
        # Write to individual participant file (for backwards compatibility)
        with open(f"data/responses/{participant.id}.json", "w") as f:
            json.dump(participant.responses, f, indent=2)
        
        # Write/append to combined CSV file (for backwards compatibility)
        csv_path = "data/responses/all_responses.csv"
        
        file_exists = os.path.isfile(csv_path)
        fieldnames = []
        
        # Define a consistent order for fields in the CSV file
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
            "demographics_nationality",
            
            # Recipe metadata
            "recipe_1_id", "recipe_1_name", "recipe_1_category",
            "recipe_2_id", "recipe_2_name", "recipe_2_category",
            "recipe_3_id", "recipe_3_name", "recipe_3_category",
            "recipe_4_id", "recipe_4_name", "recipe_4_category",
            "recipe_5_id", "recipe_5_name", "recipe_5_category",
            
            # Recipe evaluation 1
            "recipe_eval_1_recipe_id", "recipe_eval_1_recipe_name", "recipe_eval_1_recipe_category",
            "recipe_eval_1_clarity_rating", "recipe_eval_1_tastiness_rating", 
            "recipe_eval_1_completeness_rating", "recipe_eval_1_correctness_rating",
            "recipe_eval_1_ingredients_correctness", "recipe_eval_1_instructions_correctness",
            "recipe_eval_1_nutrition_correctness", "recipe_eval_1_feasibility_rating",
            "recipe_eval_1_quality_rating", "recipe_eval_1_would_make", "recipe_eval_1_comments",
            
            # Recipe evaluation 2
            "recipe_eval_2_recipe_id", "recipe_eval_2_recipe_name", "recipe_eval_2_recipe_category",
            "recipe_eval_2_clarity_rating", "recipe_eval_2_tastiness_rating", 
            "recipe_eval_2_completeness_rating", "recipe_eval_2_correctness_rating",
            "recipe_eval_2_ingredients_correctness", "recipe_eval_2_instructions_correctness",
            "recipe_eval_2_nutrition_correctness", "recipe_eval_2_feasibility_rating",
            "recipe_eval_2_quality_rating", "recipe_eval_2_would_make", "recipe_eval_2_comments",
            
            # Recipe evaluation 3
            "recipe_eval_3_recipe_id", "recipe_eval_3_recipe_name", "recipe_eval_3_recipe_category",
            "recipe_eval_3_clarity_rating", "recipe_eval_3_tastiness_rating", 
            "recipe_eval_3_completeness_rating", "recipe_eval_3_correctness_rating",
            "recipe_eval_3_ingredients_correctness", "recipe_eval_3_instructions_correctness",
            "recipe_eval_3_nutrition_correctness", "recipe_eval_3_feasibility_rating",
            "recipe_eval_3_quality_rating", "recipe_eval_3_would_make", "recipe_eval_3_comments",
            
            # Recipe evaluation 4
            "recipe_eval_4_recipe_id", "recipe_eval_4_recipe_name", "recipe_eval_4_recipe_category",
            "recipe_eval_4_clarity_rating", "recipe_eval_4_tastiness_rating", 
            "recipe_eval_4_completeness_rating", "recipe_eval_4_correctness_rating",
            "recipe_eval_4_ingredients_correctness", "recipe_eval_4_instructions_correctness",
            "recipe_eval_4_nutrition_correctness", "recipe_eval_4_feasibility_rating",
            "recipe_eval_4_quality_rating", "recipe_eval_4_would_make", "recipe_eval_4_comments",
            
            # Recipe evaluation 5
            "recipe_eval_5_recipe_id", "recipe_eval_5_recipe_name", "recipe_eval_5_recipe_category",
            "recipe_eval_5_clarity_rating", "recipe_eval_5_tastiness_rating", 
            "recipe_eval_5_completeness_rating", "recipe_eval_5_correctness_rating",
            "recipe_eval_5_ingredients_correctness", "recipe_eval_5_instructions_correctness",
            "recipe_eval_5_nutrition_correctness", "recipe_eval_5_feasibility_rating",
            "recipe_eval_5_quality_rating", "recipe_eval_5_would_make", "recipe_eval_5_comments",
            
            # Post survey
            "post_survey_cooking_skills", "post_survey_new_recipe_frequency",
            "post_survey_preferred_source", "post_survey_cooking_frequency",
            "post_survey_trust_human_recipes", "post_survey_trust_ai_recipes",
            "post_survey_ai_usage", "post_survey_comments"
        ]
        
        # Get all keys from flattened data that might not be in our ordered list
        all_keys = set(flattened_data.keys())
        
        # Add any missing keys to the end of our ordered list
        for key in all_keys:
            if key not in ordered_fieldnames:
                ordered_fieldnames.append(key)
        
        # Append to CSV file (create if not exists)
        with open(csv_path, "a" if file_exists else "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(flattened_data)
        
        # Save to database
        participant_dict = {
            "id": participant.id,
            "start_time": participant.start_time,
            "completed": participant.completed,
            "current_step": participant.current_step,
            "responses": participant.responses,
            "selected_recipes": participant.selected_recipes
        }
        save_participant(participant_dict)
        
        logger.info(f"Saved responses for participant {participant.id}")
        
    except Exception as e:
        logger.error(f"Error saving participant responses: {e}")
