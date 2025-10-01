import uvicorn
from app.main import app

if __name__ == "__main__":
    # Run the application with uvicorn
    # Host 0.0.0.0 makes it accessible from other devices on your network
    # Port 8000 is the default for FastAPI
    # Reload=True enables hot reloading for development
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
