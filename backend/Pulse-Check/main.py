from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Pulse Check API running"}
