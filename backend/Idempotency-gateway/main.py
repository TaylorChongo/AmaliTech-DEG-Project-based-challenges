from fastapi import FastAPI

app = FastAPI(title="Idempotency Gateway API")

@app.get("/")
async def root():
    return {"message": "API running"}
