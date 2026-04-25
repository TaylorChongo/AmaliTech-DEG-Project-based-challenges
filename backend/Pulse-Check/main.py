import asyncio
from datetime import datetime
from fastapi import FastAPI, status, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# In-memory storage for monitors
monitors = {}

class Monitor(BaseModel):
    id: str
    timeout: int
    alert_email: str

async def monitor_timer(monitor_id: str, timeout: int):
    """Asynchronous timer that waits for the timeout and triggers an alert."""
    await asyncio.sleep(timeout)
    if monitor_id in monitors:
        monitors[monitor_id]["status"] = "DOWN"
        alert = {
            "ALERT": f"Device {monitor_id} is down!",
            "time": datetime.now().isoformat()
        }
        print(alert)  # Simple logging

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors()},
    )

@app.get("/")
async def root():
    return {"message": "Pulse Check API running"}

@app.post("/monitors", status_code=status.HTTP_201_CREATED)
async def create_monitor(monitor: Monitor):
    if monitor.id in monitors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Monitor already exists"
        )
    
    # Create the task for the async timer
    task = asyncio.create_task(monitor_timer(monitor.id, monitor.timeout))
    
    monitors[monitor.id] = {
        "timeout": monitor.timeout,
        "status": "ACTIVE",
        "alert_email": monitor.alert_email,
        "task": task
    }
    return {
        "id": monitor.id,
        "timeout": monitor.timeout,
        "status": "ACTIVE",
        "alert_email": monitor.alert_email
    }

@app.post("/monitors/{id}/heartbeat")
async def heartbeat(id: str):
    if id not in monitors:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    
    monitor = monitors[id]
    if monitor["status"] != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Heartbeat failed: Monitor is in {monitor['status']} state"
        )
    
    # Cancel the existing timer task
    if monitor["task"]:
        monitor["task"].cancel()
    
    # Start a new timer task (reset)
    new_task = asyncio.create_task(monitor_timer(id, monitor["timeout"]))
    monitors[id]["task"] = new_task
    
    return {"message": "Heartbeat received, timer reset"}
