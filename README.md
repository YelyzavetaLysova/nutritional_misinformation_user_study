# Recipe Feasibility User Study

A FastAPI web application for conducting user studies on recipe evaluation and feasibility assessment.

## Overview

This application conducts a research study investigating how users perceive and evaluate recipes in terms of feasibility, attractiveness, and correctness. The study is designed for deployment on platforms like Prolific Academic and follows a structured survey flow:

1. **Informed Consent** - Participants read study information and provide consent
2. **Demographics** - Collection of basic demographic information
3. **Recipe Evaluations** - Evaluation of 5 randomly selected recipes (one from each category: breakfast, lunch, dinner, snack, dessert)
4. **Post-Survey Questionnaire** - Additional questions about cooking habits and preferences  
5. **Debriefing** - Study completion and participant debriefing

## Key Features

- **Mobile-optimized design** with responsive layout for various devices
- **Prolific integration** with automatic parameter handling (PROLIFIC_PID, STUDY_ID, SESSION_ID)
- **SQLite database** for robust data storage and participant tracking
- **Recipe randomization** ensuring balanced distribution across meal categories
- **Session management** with timeout protection and step validation
- **Duplicate prevention** to avoid multiple submissions from same participant
- **Comprehensive logging** for monitoring and debugging
- **Data export capabilities** for research analysis

## Project Structure

```
User study prototype/
├── app/                    # Main application package
│   ├── main.py            # FastAPI application and route handlers
│   ├── db.py              # Database operations and models
│   ├── static/css/        # Stylesheets
│   └── templates/         # HTML templates (Jinja2)
├── data/                  # Data storage
│   ├── recipes.csv        # Recipe dataset (semicolon-delimited)
│   ├── survey.db          # SQLite database
│   └── responses/         # Response data exports
├── logs/                  # Application logs
├── scripts/               # Utility scripts
├── run.py                 # Application entry point
├── prolific_config.py     # Prolific platform configuration
└── requirements.txt       # Python dependencies
```

## Setup and Installation

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Clone the repository and navigate to the User study prototype directory**
   ```bash
   cd "User study prototype"
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # OR
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python scripts/create_db.py
   ```

### Running the Application

**Development mode:**
```bash
python run.py
```
The application will be available at `http://localhost:8000`

**Production deployment:**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

## Configuration

### Environment Variables
Create a `.env` file in the root directory (optional):
```bash
DATABASE_URL=sqlite:///data/survey.db
SESSION_SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
```

### Recipe Data Format
The application expects `data/recipes.csv` with semicolon-delimited format:
```csv
Recipe_ID;Recipe_Name;Category;Ingredients;Instructions;Prep_Time;Cook_Time;Servings;Calories_per_100g;Protein_per_100g;Carbs_per_100g;Fat_per_100g;Fiber_per_100g;Sodium_per_100g
```

Categories must include: `breakfast`, `lunch`, `dinner`, `snack`, `dessert`

## Database Schema

The application uses SQLite with the following main tables:
- **participants**: Stores participant information and demographics
- **responses**: Stores recipe evaluation responses
- **study_sessions**: Tracks study progress and timing

## API Endpoints

- `GET /` - Study introduction and consent form
- `POST /start` - Initialize participant session
- `GET /demographics` - Demographics questionnaire
- `GET /recipe_eval_{1-5}` - Recipe evaluation pages
- `GET /post_survey` - Post-study questionnaire
- `GET /debriefing` - Study completion page
- `GET /admin/data` - Data export endpoint (admin only)

## Research Ethics and Data Privacy

- All data is collected anonymously with participant consent
- SQLite database stores responses securely
- Prolific integration ensures participant compensation tracking
- Session timeouts prevent incomplete data submissions
- GDPR-compliant data handling practices

## Troubleshooting

**Common Issues:**

1. **Database initialization fails**
   ```bash
   python scripts/create_db.py
   ```

2. **Recipe data not loading**
   - Check `data/recipes.csv` exists and uses semicolon delimiters
   - Verify all required columns are present

3. **Prolific parameters missing**
   - Ensure URL includes: `?PROLIFIC_PID=xxx&STUDY_ID=xxx&SESSION_ID=xxx`

4. **Session timeout issues**
   - Check `SESSION_TIMEOUT_MINUTES` in `app/main.py`
   - Review participant flow in logs

## Development

### Adding New Questions
1. Update database schema in `app/db.py`
2. Add form fields to relevant templates
3. Update route handlers in `app/main.py`

### Customizing Appearance
- Modify CSS in `app/static/css/style.css`
- Update HTML templates in `app/templates/`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions about this research study:
- **Principal Investigator**: [Name] - [email]
- **Technical Support**: [Name] - [email]

5. Start and enable the service:
   ```
   sudo systemctl start nutritional-survey
   sudo systemctl enable nutritional-survey
   ```

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
