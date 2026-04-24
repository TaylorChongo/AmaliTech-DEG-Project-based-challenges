from fastapi import FastAPI, Header, Body
from pydantic import BaseModel

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
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    return {"message": "processing..."}
