from fastapi import FastAPI

app = FastAPI(title="Smart Job Tracker API")

@app.get("/health")
def health():
    return {"status": "ok"}
