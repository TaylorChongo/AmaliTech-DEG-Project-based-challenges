from fastapi import FastAPI, Header, Body, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
import hashlib
import json
import asyncio

app = FastAPI(title="Idempotency Gateway API")

# In-memory store for idempotency
# Structure: { idempotency_key: { "hash": str, "status": str, "response": dict, "status_code": int } }
idempotency_store = {}

class PaymentRequest(BaseModel):
    amount: float
    currency: str

@app.get("/")
async def root():
    return {"message": "API running"}

@app.post("/process-payment")
async def process_payment(
    response: Response,
    payment: PaymentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key")
    
    # Compute SHA256 hash of the request body
    payload_str = json.dumps(payment.dict(), sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

    if idempotency_key in idempotency_store:
        stored_data = idempotency_store[idempotency_key]
        
        # If hashes match, return stored response
        if stored_data["hash"] == payload_hash:
            # If still processing, we might want to wait, but the task says "return stored response"
            # Assuming it's already COMPLETED for this task logic
            if stored_data["status"] == "COMPLETED":
                response.headers["X-Cache-Hit"] = "true"
                response.status_code = stored_data["status_code"]
                return stored_data["response"]
        else:
            # If hashes don't match, it's a conflict
            raise HTTPException(
                status_code=409,
                detail="Idempotency key already used for a different request body."
            )
    
    # If key doesn't exist or hash is different (different hash logic to be refined in next task)
    # For now, let's proceed with new entry or overwrite if it's a new request with same key (to be fixed)
    
    # Mark as IN_PROGRESS
    idempotency_store[idempotency_key] = {
        "hash": payload_hash,
        "status": "IN_PROGRESS",
        "response": None,
        "status_code": None
    }

    # Simulate 2 second delay
    await asyncio.sleep(2)

    # Process payment (Dummy logic)
    response_body = {"message": f"Charged {payment.amount} {payment.currency}"}
    status_code = 200

    # Update store with COMPLETED status
    idempotency_store[idempotency_key].update({
        "status": "COMPLETED",
        "response": response_body,
        "status_code": status_code
    })

    return response_body
