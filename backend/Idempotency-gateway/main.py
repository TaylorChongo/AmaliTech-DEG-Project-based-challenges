from fastapi import FastAPI, Header, Body, HTTPException
from pydantic import BaseModel
from typing import Optional

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
    return {"message": "processing..."}
