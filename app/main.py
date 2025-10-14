import os
import csv
import json
import logging
import random
from datetime import datetime, timedelta
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
SESSION_TIMEOUT_MINUTES = 60  # 60-minute session timeout
MIN_RESPONSE_TIME_SECONDS = 30  # Minimum time per recipe evaluation
MAX_RESPONSE_TIME_MINUTES = 10  # Maximum time per recipe evaluation

# Step mapping for validation
STEP_ROUTES = {
    0: "/demographics",
    1: "/recipe_eval_1", 
    2: "/recipe_eval_2",
    3: "/recipe_eval_3", 
    4: "/recipe_eval_4",
    5: "/recipe_eval_5",
    6: "/post_survey",
    7: "/debriefing"
}


class Participant(BaseModel):
    id: str
    selected_recipes: List[int]
    current_step: int = 0
    responses: Dict = {}
    completed: bool = False
    start_time: Optional[str] = None
    last_activity: Optional[str] = None
    step_times: Dict[str, str] = {}  # Track when each step was started


# In-memory participant data store (replace with a database in production)
participants = {}


def validate_step_access(participant: Optional[Participant], requested_step: int) -> bool:
    """
    Validate if participant can access the requested step.
    Returns True if access is allowed, False otherwise.
    """
    if not participant:
        return requested_step == 0  # Only allow demographics for new participants
    
    # Allow access to current step or previous completed steps
    return requested_step <= participant.current_step

def get_correct_step_redirect(participant: Optional[Participant]) -> str:
    """
    Get the correct URL to redirect participant to based on their progress.
    """
    if not participant:
        return "/demographics"
    
    # If completed, go to debriefing
    if participant.completed:
        return "/debriefing"
    
    # Otherwise, go to current step
    current_step = participant.current_step
    if current_step >= len(STEP_ROUTES):
        return "/debriefing"
    
    return STEP_ROUTES.get(current_step, "/demographics")

def is_session_expired(participant: Optional[Participant]) -> bool:
    """Check if participant's session has expired."""
    if not participant or not participant.last_activity:
        return False
    
    try:
        last_activity = datetime.fromisoformat(participant.last_activity)
        return datetime.now() - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    except Exception as e:
        logger.warning(f"Error checking session expiry: {e}")
        return False

def update_participant_activity(participant: Participant):
    """Update participant's last activity timestamp."""
    participant.last_activity = datetime.now().isoformat()

def validate_response_time(start_time: str, step_type: str) -> Dict[str, any]:
    """
    Validate response time for a step.
    Returns dict with validation info.
    """
    result = {
        "valid": True,
        "time_spent_seconds": None,
        "warning": None
    }
    
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.now()
        time_spent = (end_dt - start_dt).total_seconds()
        result["time_spent_seconds"] = time_spent
        
        # Check for suspiciously fast responses on recipe evaluations
        if step_type.startswith("recipe_eval") and time_spent < MIN_RESPONSE_TIME_SECONDS:
            result["valid"] = False
            result["warning"] = f"Response too fast: {time_spent:.1f}s (minimum: {MIN_RESPONSE_TIME_SECONDS}s)"
            logger.warning(f"Fast response detected: {time_spent:.1f}s for {step_type}")
        
        # Check for suspiciously slow responses
        elif time_spent > (MAX_RESPONSE_TIME_MINUTES * 60):
            result["warning"] = f"Response very slow: {time_spent/60:.1f}min (maximum expected: {MAX_RESPONSE_TIME_MINUTES}min)"
            logger.warning(f"Slow response detected: {time_spent/60:.1f}min for {step_type}")
        
    except Exception as e:
        logger.error(f"Error validating response time: {e}")
        result["warning"] = "Could not validate response time"
    
    return result

def validate_attention_checks(participant: Participant) -> Dict[str, any]:
    """
    Validate attention checks for a participant.
    Returns validation results.
    """
    results = {
        "recipe_attention_check_passed": None,
        "post_survey_attention_check_passed": None,
        "overall_passed": True
    }
    
    # Check recipe evaluation attention check (step 3)
    recipe_eval_3 = participant.responses.get("recipe_eval_3", {})
    if "attention_check_recipe" in recipe_eval_3:
        expected_answer = 3  # Should select "3" on the scale
        actual_answer = recipe_eval_3.get("attention_check_recipe")
        passed = actual_answer == expected_answer
        results["recipe_attention_check_passed"] = passed
        if not passed:
            logger.warning(f"Recipe attention check failed for {participant.id}: expected {expected_answer}, got {actual_answer}")
            results["overall_passed"] = False
    
    # Check post-survey attention check
    post_survey = participant.responses.get("post_survey", {})
    if "attention_check_post" in post_survey:
        expected_answer = "gemini"  # Should select "gemini" from dropdown
        actual_answer = post_survey.get("attention_check_post")
        passed = actual_answer == expected_answer
        results["post_survey_attention_check_passed"] = passed
        if not passed:
            logger.warning(f"Post-survey attention check failed for {participant.id}: expected '{expected_answer}', got '{actual_answer}'")
            results["overall_passed"] = False
    
    return results

def detect_session_manipulation(participant_id: str, prolific_pid: str = None) -> Dict[str, any]:
    """
    Detect potential session manipulation attempts.
    Returns detection results.
    """
    results = {
        "multiple_sessions_detected": False,
        "session_details": [],
        "warning": None
    }
    
    if not prolific_pid:
        return results
    
    try:
        # Check for multiple sessions with same Prolific ID
        from app.db import check_prolific_duplicate
        duplicates = check_prolific_duplicate(prolific_pid)
        
        if len(duplicates) > 1:
            results["multiple_sessions_detected"] = True
            results["session_details"] = duplicates
            results["warning"] = f"Multiple sessions detected for Prolific ID {prolific_pid}: {len(duplicates)} sessions"
            logger.warning(f"Session manipulation detected: {results['warning']}")
        
        logger.info(f"Session manipulation check for {participant_id} (Prolific: {prolific_pid}): {len(duplicates)} sessions found")
        
    except Exception as e:
        logger.error(f"Error detecting session manipulation: {e}")
        results["warning"] = "Could not check for session manipulation"
    
    return results
    """
    Validate response time for a step.
    Returns dict with validation info.
    """
    result = {
        "valid": True,
        "time_spent_seconds": None,
        "warning": None
    }
    
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.now()
        time_spent = (end_dt - start_dt).total_seconds()
        result["time_spent_seconds"] = time_spent
        
        # Check for suspiciously fast responses on recipe evaluations
        if step_type.startswith("recipe_eval") and time_spent < MIN_RESPONSE_TIME_SECONDS:
            result["valid"] = False
            result["warning"] = f"Response too fast: {time_spent:.1f}s (minimum: {MIN_RESPONSE_TIME_SECONDS}s)"
            logger.warning(f"Fast response detected: {time_spent:.1f}s for {step_type}")
        
        # Check for suspiciously slow responses
        elif time_spent > (MAX_RESPONSE_TIME_MINUTES * 60):
            result["warning"] = f"Response very slow: {time_spent/60:.1f}min (maximum expected: {MAX_RESPONSE_TIME_MINUTES}min)"
            logger.warning(f"Slow response detected: {time_spent/60:.1f}min for {step_type}")
        
    except Exception as e:
        logger.error(f"Error validating response time: {e}")
        result["warning"] = "Could not validate response time"
    
    return result


def get_participant_from_session(request: Request) -> Optional[Participant]:
    """Get participant data from session or create a new participant."""
    if "participant_id" not in request.session:
        return None
    
    participant_id = request.session.get("participant_id")
    
    # First try to get from in-memory cache
    if participant_id in participants:
        participant = participants[participant_id]
        
        # Check session expiry
        if is_session_expired(participant):
            logger.warning(f"Session expired for participant {participant_id}")
            # Clear session
            request.session.clear()
            return None
        
        # Update activity timestamp
        update_participant_activity(participant)
        return participant
    
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
            "education": participant_row.get("education")
        }
        
        # Add evaluations to responses
        for eval_data in evaluations:
            eval_number = eval_data.get("eval_number")
            responses[f"recipe_eval_{eval_number}"] = {
                "recipe_id": eval_data.get("recipe_id"),
                "recipe_name": eval_data.get("recipe_name"),
                "recipe_category": eval_data.get("recipe_category"),
                "completeness_rating": eval_data.get("completeness_rating"),
                "healthiness_rating": eval_data.get("healthiness_rating"),
                "tastiness_rating": eval_data.get("tastiness_rating"),
                "feasibility_rating": eval_data.get("feasibility_rating"),
                "would_make": eval_data.get("would_make"),
                "ingredients_complexity": eval_data.get("ingredients_complexity"),
                "instructions_complexity": eval_data.get("instructions_complexity"),
                "ingredients_correctness": eval_data.get("ingredients_correctness"),
                "instructions_correctness": eval_data.get("instructions_correctness"),
                "nutrition_correctness": eval_data.get("nutrition_correctness"),
                "comments": eval_data.get("comments", "")
            }
            
            # Track recipe IDs
            if eval_data.get("recipe_id") is not None:
                selected_recipes.append(eval_data.get("recipe_id"))
        
        # Add post survey if available
        if post_survey:
            # Handle recipe_factors as JSON string from database
            recipe_factors = post_survey.get("recipe_factors", "[]")
            if isinstance(recipe_factors, str):
                try:
                    import json
                    recipe_factors = json.loads(recipe_factors)
                except:
                    recipe_factors = []
            
            responses["post_survey"] = {
                "cooking_skills": post_survey.get("cooking_skills"),
                "new_recipe_frequency": post_survey.get("new_recipe_frequency"),
                "recipe_factors": recipe_factors,
                "recipe_usage_frequency": post_survey.get("recipe_usage_frequency"),
                "cooking_frequency": post_survey.get("cooking_frequency"),
                "trust_human_recipes": post_survey.get("trust_human_recipes"),
                "trust_ai_recipes": post_survey.get("trust_ai_recipes"),
                "ai_recipe_usage": post_survey.get("ai_recipe_usage"),
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
            start_time=participant_row.get("start_time"),
            last_activity=participant_row.get("last_activity_at"),
            step_times={}  # Initialize empty step times
        )
        
        # Check session expiry
        if is_session_expired(participant):
            logger.warning(f"Session expired for participant {participant_id}")
            return None
        
        # Update activity timestamp
        update_participant_activity(participant)
        
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
        start_time=datetime.now().isoformat(),
        last_activity=datetime.now().isoformat()
    )
    
    participants[participant_id] = participant
    logger.info(f"Created new participant {participant_id} with recipes {selected_recipes}")
    
    return participant


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Homepage with study information and consent form."""
    # Capture Prolific parameters if present
    prolific_pid = request.query_params.get("PROLIFIC_PID")
    study_id = request.query_params.get("STUDY_ID")
    session_id = request.query_params.get("SESSION_ID")
    
    # Store Prolific parameters in template context
    context = {
        "request": request,
        "prolific_pid": prolific_pid,
        "study_id": study_id,
        "session_id": session_id
    }
    
    return templates.TemplateResponse("index.html", context)


@app.post("/start")
async def start_survey(
    request: Request,
    prolific_pid: str = Form(None),
    study_id: str = Form(None),
    session_id: str = Form(None)
):
    """Initialize a new participant session."""
    # Debug logging for Prolific parameters
    logger.info(f"Prolific parameters received: PID={prolific_pid}, STUDY_ID={study_id}, SESSION_ID={session_id}")
    
    # Check for session manipulation if Prolific participant
    if prolific_pid:
        manipulation_check = detect_session_manipulation("new_participant", prolific_pid)
        if manipulation_check["multiple_sessions_detected"]:
            logger.warning(f"Potential session manipulation detected for Prolific ID {prolific_pid}")
            # You could choose to block the participant here or just flag it
            # For now, we'll continue but log the warning
    
    participant = create_new_participant()
    
    # Store Prolific information if provided
    if prolific_pid:
        participant.responses["prolific_info"] = {
            "prolific_pid": prolific_pid,
            "study_id": study_id,
            "session_id": session_id
        }
        
        # Store session manipulation check results
        participant.responses["session_manipulation_check"] = detect_session_manipulation(participant.id, prolific_pid)
        
        logger.info(f"Starting survey with Prolific participant {prolific_pid}")
        logger.info(f"Prolific info stored: {participant.responses['prolific_info']}")
    else:
        logger.info("No Prolific parameters - regular participant")
    
    request.session["participant_id"] = participant.id
    logger.info(f"Starting survey with participant {participant.id}")
    return RedirectResponse(url="/demographics", status_code=303)


@app.get("/demographics", response_class=HTMLResponse)
async def demographics_form(request: Request, participant: Participant = Depends(get_participant_from_session)):
    """Demographics data collection form."""
    # Step validation: Only allow access to demographics (step 0)
    if not validate_step_access(participant, 0):
        redirect_url = get_correct_step_redirect(participant)
        logger.warning(f"Unauthorized access attempt to demographics. Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    # Track step start time
    if participant:
        participant.step_times["demographics"] = datetime.now().isoformat()
    
    return templates.TemplateResponse("demographics.html", {"request": request})


@app.post("/demographics")
async def submit_demographics(
    request: Request,
    age: str = Form(...),
    gender: str = Form(...),
    education: str = Form(...),
    participant: Participant = Depends(get_participant_from_session)
):
    """Process demographics form submission."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Validate response time
    step_start_time = participant.step_times.get("demographics")
    if step_start_time:
        time_validation = validate_response_time(step_start_time, "demographics")
        if time_validation["warning"]:
            logger.info(f"Demographics timing warning for {participant.id}: {time_validation['warning']}")
    
    # Store demographics data
    participant.responses["demographics"] = {
        "age": age,
        "gender": gender,
        "education": education
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
    
    # Step validation: Check if participant can access this recipe evaluation step
    if not validate_step_access(participant, step_id):
        redirect_url = get_correct_step_redirect(participant)
        logger.warning(f"Unauthorized access attempt to recipe_eval_{step_id}. Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    if step_id < 1 or step_id > NUM_RECIPES_PER_PARTICIPANT:
        raise HTTPException(status_code=404, detail="Invalid step")
    
    # Track step start time
    participant.step_times[f"recipe_eval_{step_id}"] = datetime.now().isoformat()
    
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
    completeness_rating: int = Form(...),
    healthiness_rating: int = Form(...),
    tastiness_rating: int = Form(...),
    feasibility_rating: int = Form(...),
    would_make: int = Form(...),
    ingredients_complexity: int = Form(...),
    instructions_complexity: int = Form(...),
    ingredients_correctness: int = Form(...),
    instructions_correctness: int = Form(...),
    nutrition_correctness: int = Form(...),
    comments: str = Form(None),
    attention_check_recipe: int = Form(None),
    participant: Participant = Depends(get_participant_from_session)
):
    """Process recipe evaluation submission."""
    # Log form data for debugging
    form_data = await request.form()
    logger.info(f"Recipe evaluation form submission data for step {step_id}: {dict(form_data)}")
    
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Step validation: Check if participant can submit this step
    if not validate_step_access(participant, step_id):
        redirect_url = get_correct_step_redirect(participant)
        logger.warning(f"Unauthorized submission attempt to recipe_eval_{step_id}. Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    if step_id < 1 or step_id > NUM_RECIPES_PER_PARTICIPANT:
        raise HTTPException(status_code=404, detail="Invalid step")
    
    # Validate response time
    step_start_time = participant.step_times.get(f"recipe_eval_{step_id}")
    if step_start_time:
        time_validation = validate_response_time(step_start_time, f"recipe_eval_{step_id}")
        if time_validation["warning"]:
            logger.info(f"Recipe eval {step_id} timing warning for {participant.id}: {time_validation['warning']}")
        
        # Store response time in evaluation data
        eval_data = {
            "response_time_seconds": time_validation.get("time_spent_seconds")
        }
    else:
        eval_data = {}
    
    # Store evaluation data
    recipe_index = participant.selected_recipes[step_id - 1]
    recipe = recipes_df.iloc[recipe_index]
    
    eval_data.update({
        "recipe_id": recipe_index,
        "recipe_name": recipe_name,
        "recipe_category": recipe["Category"],
        "completeness_rating": completeness_rating,
        "healthiness_rating": healthiness_rating,
        "tastiness_rating": tastiness_rating,
        "feasibility_rating": feasibility_rating,
        "would_make": would_make,
        "ingredients_complexity": ingredients_complexity,
        "instructions_complexity": instructions_complexity,
        "ingredients_correctness": ingredients_correctness,
        "instructions_correctness": instructions_correctness,
        "nutrition_correctness": nutrition_correctness,
        "comments": comments or ""
    })
    
    # Only add attention check for step 3
    if step_id == 3:
        eval_data["attention_check_recipe"] = attention_check_recipe
    
    participant.responses[f"recipe_eval_{step_id}"] = eval_data
    
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
    
    # Step validation: Check if participant can access post-survey (step 6)
    if not validate_step_access(participant, 6):
        redirect_url = get_correct_step_redirect(participant)
        logger.warning(f"Unauthorized access attempt to post_survey. Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    # Track step start time
    participant.step_times["post_survey"] = datetime.now().isoformat()
    
    return templates.TemplateResponse("post_survey.html", {"request": request})


@app.post("/post_survey")
async def submit_post_survey(
    request: Request,
    cooking_skills: int = Form(...),
    new_recipe_frequency: str = Form(...),
    recipe_factors: List[str] = Form([]),
    recipe_usage_frequency: str = Form(...),
    cooking_frequency: str = Form(...),
    trust_human_recipes: int = Form(...),
    trust_ai_recipes: int = Form(...),
    ai_recipe_usage: str = Form(...),
    comments: str = Form(None),
    attention_check_post: str = Form(...),
    participant: Participant = Depends(get_participant_from_session)
):
    """Process post-survey submission."""
    # Log form data for debugging
    form_data = await request.form()
    logger.info(f"Post-survey form submission data: {dict(form_data)}")
    
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    # Step validation: Check if participant can submit post-survey (step 6)
    if not validate_step_access(participant, 6):
        redirect_url = get_correct_step_redirect(participant)
        logger.warning(f"Unauthorized submission attempt to post_survey. Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    # Validate response time
    step_start_time = participant.step_times.get("post_survey")
    if step_start_time:
        time_validation = validate_response_time(step_start_time, "post_survey")
        if time_validation["warning"]:
            logger.info(f"Post-survey timing warning for {participant.id}: {time_validation['warning']}")
    
    # Store post-survey data
    participant.responses["post_survey"] = {
        "cooking_skills": cooking_skills,
        "new_recipe_frequency": new_recipe_frequency,
        "recipe_factors": recipe_factors,
        "recipe_usage_frequency": recipe_usage_frequency,
        "cooking_frequency": cooking_frequency,
        "trust_human_recipes": trust_human_recipes,
        "trust_ai_recipes": trust_ai_recipes,
        "ai_recipe_usage": ai_recipe_usage,
        "comments": comments or "",
        "attention_check_post": attention_check_post
    }
    
    # Update participant progress
    participant.current_step = 7  # Move to debriefing step
    
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
    
    # Step validation: Check if participant can access debriefing (step 7)
    if not validate_step_access(participant, 7):
        redirect_url = get_correct_step_redirect(participant)
        logger.warning(f"Unauthorized access attempt to debriefing. Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    # Mark participant as completed
    participant.completed = True
    participant.responses["completed_time"] = datetime.now().isoformat()
    
    # Validate attention checks and log results
    attention_check_results = validate_attention_checks(participant)
    participant.responses["attention_check_validation"] = attention_check_results
    logger.info(f"Attention check validation for {participant.id}: {attention_check_results}")
    
    # Save final responses
    save_participant_responses(participant)
    
    logger.info(f"Participant {participant.id} completed the study")
    
    # Check if this is a Prolific participant
    prolific_info = participant.responses.get("prolific_info")
    context = {
        "request": request,
        "is_prolific": prolific_info is not None,
        "prolific_pid": prolific_info.get("prolific_pid") if prolific_info else None
    }
    
    return templates.TemplateResponse("debriefing.html", context)


@app.get("/complete")
async def complete_study(request: Request, participant: Participant = Depends(get_participant_from_session)):
    """Redirect to Prolific completion URL."""
    if not participant:
        return RedirectResponse(url="/", status_code=303)
    
    if not participant.completed:
        return RedirectResponse(url=f"/{REQUIRED_STEPS[participant.current_step]}", status_code=303)
    
    # Use the configured Prolific completion URL
    try:
        from prolific_config import PROLIFIC_COMPLETION_URL
        completion_url = PROLIFIC_COMPLETION_URL
    except ImportError:
        completion_url = "https://app.prolific.co/submissions/complete?cc=C12345AB"
    
    logger.info(f"Redirecting participant {participant.id} to Prolific completion")
    
    return RedirectResponse(url=completion_url, status_code=303)


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
            
            # Recipe metadata
            "recipe_1_id", "recipe_1_name", "recipe_1_category",
            "recipe_2_id", "recipe_2_name", "recipe_2_category",
            "recipe_3_id", "recipe_3_name", "recipe_3_category",
            "recipe_4_id", "recipe_4_name", "recipe_4_category",
            "recipe_5_id", "recipe_5_name", "recipe_5_category",
            
            # Recipe evaluation 1
            "recipe_eval_1_recipe_id", "recipe_eval_1_recipe_name", "recipe_eval_1_recipe_category",
            "recipe_eval_1_completeness_rating", "recipe_eval_1_healthiness_rating", 
            "recipe_eval_1_tastiness_rating", "recipe_eval_1_feasibility_rating",
            "recipe_eval_1_would_make", "recipe_eval_1_ingredients_complexity", 
            "recipe_eval_1_instructions_complexity", "recipe_eval_1_ingredients_correctness", 
            "recipe_eval_1_instructions_correctness", "recipe_eval_1_nutrition_correctness", 
            "recipe_eval_1_comments", "recipe_eval_1_attention_check_recipe", "recipe_eval_1_response_time_seconds",
            
            # Recipe evaluation 2
            "recipe_eval_2_recipe_id", "recipe_eval_2_recipe_name", "recipe_eval_2_recipe_category",
            "recipe_eval_2_completeness_rating", "recipe_eval_2_healthiness_rating", 
            "recipe_eval_2_tastiness_rating", "recipe_eval_2_feasibility_rating",
            "recipe_eval_2_would_make", "recipe_eval_2_ingredients_complexity", 
            "recipe_eval_2_instructions_complexity", "recipe_eval_2_ingredients_correctness", 
            "recipe_eval_2_instructions_correctness", "recipe_eval_2_nutrition_correctness", 
            "recipe_eval_2_comments", "recipe_eval_2_attention_check_recipe", "recipe_eval_2_response_time_seconds",
            
            # Recipe evaluation 3 (with attention check)
            "recipe_eval_3_recipe_id", "recipe_eval_3_recipe_name", "recipe_eval_3_recipe_category",
            "recipe_eval_3_completeness_rating", "recipe_eval_3_healthiness_rating", 
            "recipe_eval_3_tastiness_rating", "recipe_eval_3_feasibility_rating",
            "recipe_eval_3_would_make", "recipe_eval_3_ingredients_complexity", 
            "recipe_eval_3_instructions_complexity", "recipe_eval_3_ingredients_correctness", 
            "recipe_eval_3_instructions_correctness", "recipe_eval_3_nutrition_correctness", 
            "recipe_eval_3_comments", "recipe_eval_3_attention_check_recipe", "recipe_eval_3_response_time_seconds",
            
            # Recipe evaluation 4
            "recipe_eval_4_recipe_id", "recipe_eval_4_recipe_name", "recipe_eval_4_recipe_category",
            "recipe_eval_4_completeness_rating", "recipe_eval_4_healthiness_rating", 
            "recipe_eval_4_tastiness_rating", "recipe_eval_4_feasibility_rating",
            "recipe_eval_4_would_make", "recipe_eval_4_ingredients_complexity", 
            "recipe_eval_4_instructions_complexity", "recipe_eval_4_ingredients_correctness", 
            "recipe_eval_4_instructions_correctness", "recipe_eval_4_nutrition_correctness", 
            "recipe_eval_4_comments", "recipe_eval_4_attention_check_recipe", "recipe_eval_4_response_time_seconds",
            
            # Recipe evaluation 5
            "recipe_eval_5_recipe_id", "recipe_eval_5_recipe_name", "recipe_eval_5_recipe_category",
            "recipe_eval_5_completeness_rating", "recipe_eval_5_healthiness_rating", 
            "recipe_eval_5_tastiness_rating", "recipe_eval_5_feasibility_rating",
            "recipe_eval_5_would_make", "recipe_eval_5_ingredients_complexity", 
            "recipe_eval_5_instructions_complexity", "recipe_eval_5_ingredients_correctness", 
            "recipe_eval_5_instructions_correctness", "recipe_eval_5_nutrition_correctness", 
            "recipe_eval_5_comments", "recipe_eval_5_response_time_seconds",
            
            # Post survey
            "post_survey_cooking_skills", "post_survey_new_recipe_frequency",
            "post_survey_recipe_factors", "post_survey_recipe_usage_frequency", "post_survey_cooking_frequency",
            "post_survey_trust_human_recipes", "post_survey_trust_ai_recipes",
            "post_survey_ai_recipe_usage", "post_survey_comments", "post_survey_attention_check_post"
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
            "step_completed_at": datetime.now().isoformat(),
            "last_activity_at": participant.last_activity,
            "responses": participant.responses,
            "selected_recipes": participant.selected_recipes
        }
        save_participant(participant_dict)
        
        logger.info(f"Saved responses for participant {participant.id}")
        
    except Exception as e:
        logger.error(f"Error saving participant responses: {e}")

@app.get("/admin/quality_metrics")
async def admin_quality_metrics(request: Request):
    """Admin endpoint: Get data quality metrics."""
    try:
        from app.db import get_quality_metrics
        metrics = get_quality_metrics()
        return {"status": "success", "metrics": metrics}
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/participants_quality")
async def admin_participants_quality(request: Request):
    """Admin endpoint: Get all participants with quality flags."""
    try:
        from app.db import get_participants_with_quality_flags
        participants = get_participants_with_quality_flags()
        return {"status": "success", "participants": participants}
    except Exception as e:
        logger.error(f"Error getting participants with quality flags: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/export_data")
async def admin_export_data(request: Request):
    """Admin endpoint: Export data to CSV files."""
    try:
        from app.db import export_to_csv
        success = export_to_csv()
        if success:
            return {"status": "success", "message": "Data exported to CSV files in data/normalized/"}
        else:
            return {"status": "error", "message": "Failed to export data"}
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard for monitoring survey data quality."""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})
