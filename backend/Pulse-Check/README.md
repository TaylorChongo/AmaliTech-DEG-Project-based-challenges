# Pulse-Check (Dead Man’s Switch) API

Pulse-Check is a robust Python-based API built with FastAPI designed to monitor the health and connectivity of remote devices or services. It acts as a "Dead Man’s Switch," where devices must periodically send a "heartbeat" to prove they are still functional. If a heartbeat is missed beyond a configured timeout (plus a grace period), the system triggers an alert.

## Architecture

The following diagram illustrates the lifecycle of a monitor, including registration, heartbeat resets, the grace period, and the pause/resume functionality.

```mermaid
sequenceDiagram
    participant Device
    participant API
    participant Timer
    participant Logger

    Device->>API: POST /monitors (id, timeout)
    API->>Timer: Start Async Task (timeout + grace)
    API-->>Device: 201 Created (ACTIVE)

    Note over Device, Timer: Normal Operation
    Device->>API: POST /monitors/{id}/heartbeat
    API->>Timer: Cancel existing task
    API->>Timer: Start new Task (timeout + grace)
    API-->>Device: 200 OK

    Note over Device, Timer: Pause Feature
    Device->>API: POST /monitors/{id}/pause
    API->>Timer: Cancel task
    API-->>Device: 200 OK (PAUSED)

    Note over Device, Timer: Resume via Heartbeat
    Device->>API: POST /monitors/{id}/heartbeat
    API->>Timer: Start new Task (timeout + grace)
    API-->>Device: 200 OK (ACTIVE)

    Note over Device, Timer: Timeout Scenario
    Timer->>Timer: Wait (timeout + grace)
    Timer->>API: Set status = DOWN
    API->>Logger: Log Alert (Device Down!)
```

## Setup Instructions

### Prerequisites
- Python 3.10+

### Installation
1. Clone the repository and navigate to the project directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App
Start the server using Uvicorn:
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## API Documentation

### 1. Register Monitor
**POST** `/monitors`
- **Request Body:**
  ```json
  {
    "id": "device-123",
    "timeout": 60,
    "alert_email": "admin@example.com"
  }
  ```
- **Success Response (201 Created):**
  ```json
  {
    "id": "device-123",
    "timeout": 60,
    "status": "ACTIVE",
    "alert_email": "admin@example.com"
  }
  ```

### 2. Send Heartbeat
**POST** `/monitors/{id}/heartbeat`
- **Description:** Resets the timer for an ACTIVE monitor or resumes a PAUSED monitor.
- **Success Response (200 OK):**
  ```json
  {
    "message": "Heartbeat received, monitoring active"
  }
  ```

### 3. Pause Monitor
**POST** `/monitors/{id}/pause`
- **Description:** Stops the timer completely. No alerts will fire until a heartbeat is received.
- **Success Response (200 OK):**
  ```json
  {
    "message": "Monitor paused"
  }
  ```

## Design Decisions

- **Asyncio:** Used for non-blocking concurrency. Each monitor runs its own lightweight `asyncio.create_task`, allowing the API to handle thousands of concurrent timers without the overhead of threads or processes.
- **In-Memory Store:** A Python dictionary is used for rapid prototyping and low-latency access. It stores monitor metadata and references to active `asyncio` tasks.
- **Timer Management:** Timers are managed by creating and cancelling `asyncio` tasks. When a heartbeat or pause request is received, the existing task is explicitly cancelled to prevent redundant alerts.

## Developer’s Choice: Grace Period

### What is it?
A fixed 5-second buffer (`GRACE_PERIOD = 5`) added to every monitor's timeout.

### Why it was added?
In real-world networks, packets can be delayed due to jitter or temporary congestion. Without a grace period, a device that sends a heartbeat at exactly 60 seconds might be flagged as "DOWN" if the packet arrives at 60.1 seconds.

### How it improves reliability?
By waiting for `timeout + 5` seconds, we significantly reduce false-positive alerts, ensuring that the system only triggers when a device is truly unresponsive.

## Testing

Run the automated test suite using `pytest`:
```bash
pytest test_main.py
```
