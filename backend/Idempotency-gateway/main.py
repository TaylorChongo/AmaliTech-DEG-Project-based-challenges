from fastapi import FastAPI, Header, Body, HTTPException
from pydantic import BaseModel
from typing import Optional
import hashlib
import json

app = FastAPI(title="Idempotency Gateway API")

class PaymentRequest(BaseModel):
    amount: float
    currency: str

@app.get("/")
async def root():
    return {"message": "API running"}

@app.post("/process-payment")
async def process_payment(
    payment: PaymentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key")
    
    # Compute SHA256 hash of the request body
    payload_str = json.dumps(payment.dict(), sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
    
    return {
        "message": "processing...",
        "request_hash": payload_hash
    }
