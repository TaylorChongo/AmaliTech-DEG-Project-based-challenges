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
# Locks to handle concurrent requests for the same key
locks = {}

class PaymentRequest(BaseModel):
    amount: float
    currency: str

@app.get("/")
async def root():
    return {"message": "API running"}

@app.get("/payment-status/{idempotency_key}")
async def get_payment_status(idempotency_key: str):
    if idempotency_key not in idempotency_store:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    stored_data = idempotency_store[idempotency_key]
    
    if stored_data["status"] == "IN_PROGRESS":
        return {"status": "IN_PROGRESS"}
    
    return stored_data["response"]

@app.post("/process-payment")
async def process_payment(
    response: Response,
    payment: PaymentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key")
    
    # Compute SHA256 hash of the request body
    payload_str = json.dumps(payment.model_dump(), sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

    # Get or create a lock for this specific idempotency key
    if idempotency_key not in locks:
        locks[idempotency_key] = asyncio.Lock()
    
    async with locks[idempotency_key]:
        # Check if we already have a record for this key
        if idempotency_key in idempotency_store:
            stored_data = idempotency_store[idempotency_key]
            
            # If hashes match, return stored response
            if stored_data["hash"] == payload_hash:
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
        
        # If we reached here, it's a new request (not in store) or 
        # it was a concurrent request that just finished waiting for the lock.
        # But wait, if it was concurrent and just finished, the 'if idempotency_key in idempotency_store' 
        # above would have caught it and returned. So this part is only for the first execution.

        # Mark as IN_PROGRESS
        idempotency_store[idempotency_key] = {
            "hash": payload_hash,
            "status": "IN_PROGRESS",
            "response": None,
            "status_code": None
        }

        # Simulate 2 second delay (representing heavy processing)
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
