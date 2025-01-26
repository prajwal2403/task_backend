from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Dict
from pydantic import BaseModel
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://task-frontend-flame.vercel.app"],  # Allow requests from these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Define data models
class Student(BaseModel):
    id: int
    name: str

class Task(BaseModel):
    id: int
    name: str
    baseValue: int

# Initialize students and tasks with provided data
students = [
    Student(id=1, name="Mithilesh"),
    Student(id=2, name="Krushna"),
    Student(id=3, name="Siddhant"),
    Student(id=4, name="Prajwal"),
    Student(id=5, name="Sanket"),
]

tasks = [
    Task(id=1, name="Balcony", baseValue=5),
    Task(id=2, name="Bathroom", baseValue=5),
    Task(id=3, name="Washroom", baseValue=5),
    Task(id=4, name="Kitchen", baseValue=5),
    Task(id=5, name="Basin+floor", baseValue=5),
]

# Task assignments: Maps student ID to task ID
task_assignments: Dict[int, int] = {}

# Track the last assigned task index
last_assigned_task_index = -1

# Function to assign tasks sequentially
def assign_tasks():
    global task_assignments, last_assigned_task_index
    logger.info("Assigning tasks...")
    for student in students:
        # Increment the task index (cycle back to 0 if it exceeds the list length)
        last_assigned_task_index = (last_assigned_task_index + 1) % len(tasks)
        # Assign the next task to the student
        task_assignments[student.id] = tasks[last_assigned_task_index].id
        logger.info(f"Assigned {tasks[last_assigned_task_index].name} to {student.name}")
    logger.info(f"Updated task assignments: {task_assignments}")

# Function to check if it's Saturday
def is_saturday():
    return datetime.now().weekday() == 5  # 5 corresponds to Saturday

# Initialize task assignments
assign_tasks()

# Background task to check for Saturdays and update tasks
async def check_saturday_and_update_tasks():
    while True:
        if is_saturday():
            assign_tasks()
            logger.info("Tasks updated because it's Saturday!")
        # Sleep for 24 hours before checking again
        await asyncio.sleep(86400)  # 86400 seconds = 24 hours

# Start the background task when the application starts
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_saturday_and_update_tasks())

# Endpoint to get current task assignments
@app.get("/tasks", response_model=Dict[str, str])
async def get_tasks():
    # Map student and task IDs to their names for the response
    return {
        student.name: next(task.name for task in tasks if task.id == task_assignments[student.id])
        for student in students
    }

# Endpoint to manually trigger task update
@app.post("/update-tasks")
async def update_tasks():
    assign_tasks()
    return {"message": "Tasks updated successfully!"}

# Endpoint to add a new student
@app.post("/add-student")
async def add_student(student: Student):
    if any(s.id == student.id for s in students):
        raise HTTPException(status_code=400, detail="Student already exists!")
    students.append(student)
    assign_tasks()  # Reassign tasks to include the new student
    return {"message": f"Student {student.name} added successfully!"}

# Endpoint to add a new task
@app.post("/add-task")
async def add_task(task: Task):
    if any(t.id == task.id for t in tasks):
        raise HTTPException(status_code=400, detail="Task already exists!")
    tasks.append(task)
    assign_tasks()  # Reassign tasks to include the new task
    return {"message": f"Task {task.name} added successfully!"}

# Endpoint to check if it's Saturday
@app.get("/is-saturday")
async def check_saturday():
    return {"is_saturday": is_saturday()}

# Endpoint to simulate time passing (for testing purposes)
@app.post("/simulate-time")
async def simulate_time(days: int):
    global task_assignments
    simulated_date = datetime.now() + timedelta(days=days)
    if simulated_date.weekday() == 5:  # If it's Saturday after simulation
        assign_tasks()
    return {"message": f"Simulated {days} days. Tasks updated if it's Saturday."}