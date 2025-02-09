from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
API_KEY = os.getenv("API_KEY", "prajwal2403")  # Change this or set it in environment variables
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://task-frontend-flame.vercel.app/").split(",")  # Allow all origins by default

app = FastAPI(title="Roommate Task Distribution",
             description="API for managing and distributing household tasks among roommates")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define data models
class Roommate(BaseModel):
    id: int
    name: str

class Task(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

# Initialize roommates and tasks
roommates = [
    Roommate(id=1, name="Mithilesh"),
    Roommate(id=2, name="Krushna"),
    Roommate(id=3, name="Siddant"),
    Roommate(id=4, name="Prajwal"),
    Roommate(id=5, name="Sanket"),
]

tasks = [
    Task(id=1, name="Balcony", description="Clean Appliance, Dusting, Mopping"),
    Task(id=2, name="Bathroom", description="Clean bathroom, restock supplies"),
    Task(id=3, name="washroom", description="Clean washroom, restock supplies"),
    Task(id=4, name="kitchen", description="cleaning kitchen, Dusitng, Mopping"),
    Task(id=5, name="Basin+Floor", description="Wash basin + floor"),
]

# Task assignments: Maps roommate ID to task ID
task_assignments: Dict[int, int] = {}

# Track the last assigned task index
last_assigned_task_index = -1

# Modify the assign_tasks function to properly rotate tasks
def assign_tasks():
    """Assign tasks to roommates in a circular rotation"""
    global task_assignments, last_assigned_task_index
    logger.info("Starting task rotation...")
    
    # Get current assignments if they exist
    current_assignments = {}
    if task_assignments:
        current_assignments = {k: v for k, v in task_assignments.items()}
    
    # Rotate tasks - each roommate gets the next task in the list
    for roommate in roommates:
        if not current_assignments:
            # First time assignment
            next_task_id = (roommate.id - 1) % len(tasks) + 1
        else:
            # Get current task ID for this roommate
            current_task_id = current_assignments[roommate.id]
            # Assign next task (if at end of list, go back to first task)
            next_task_id = (current_task_id % len(tasks)) + 1
            
        task_assignments[roommate.id] = next_task_id
        logger.info(f"Assigned Task {next_task_id} to {roommate.name}")
    
    logger.info(f"New task assignments: {task_assignments}")

def is_saturday():
    """Check if current day is Saturday"""
    return datetime.now().weekday() == 5

# Initialize task assignments
assign_tasks()

# Background task to check for Saturdays and update tasks
async def check_saturday_and_update_tasks():
    while True:
        try:
            if is_saturday():
                assign_tasks()
                logger.info("Tasks updated for the new week!")
            await asyncio.sleep(3600)  # Check every hour
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_saturday_and_update_tasks())

# Authorization dependency
def authorize(api_key: Optional[str] = Header(None)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key")
    return True

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "active", "message": "Roommate Task Distribution System is running"}

@app.get("/tasks", response_model=Dict[str, dict])
async def get_tasks():
    """Get current task assignments with details"""
    return {
        roommate.name: {
            "task": next(task.name for task in tasks if task.id == task_assignments[roommate.id]),
            "description": next(task.description for task in tasks if task.id == task_assignments[roommate.id])
        }
        for roommate in roommates
    }
@app.post("/update-tasks")
async def update_tasks(authorized: bool = Depends(authorize)):
    """Manually update task assignments (requires API key)"""
    logger.info("Before update - Current assignments: %s", task_assignments)
    assign_tasks()
    logger.info("After update - New assignments: %s", task_assignments)
    current_assignments = await get_tasks()
    logger.info("Formatted assignments: %s", current_assignments)
    return {"message": "Tasks reassigned successfully!", "new_assignments": current_assignments}

@app.post("/roommates")
async def add_roommate(roommate: Roommate, authorized: bool = Depends(authorize)):
    """Add a new roommate (requires API key)"""
    if any(r.id == roommate.id for r in roommates):
        raise HTTPException(status_code=400, detail="Roommate ID already exists")
    roommates.append(roommate)
    assign_tasks()
    return {"message": f"Roommate {roommate.name} added successfully"}

@app.post("/tasks/add")
async def add_task(task: Task, authorized: bool = Depends(authorize)):
    """Add a new task (requires API key)"""
    if any(t.id == task.id for t in tasks):
        raise HTTPException(status_code=400, detail="Task ID already exists")
    tasks.append(task)
    assign_tasks()
    return {"message": f"Task {task.name} added successfully"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)