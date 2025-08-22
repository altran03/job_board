from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import schemas, models
from .db import Base, engine, get_db
from .email_parser import process_gmail_applications

app = FastAPI(title="Smart Job Tracker API")

# Create tables (simple for MVP; later replace with Alembic migrations)
Base.metadata.create_all(bind=engine)

# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs", response_model=schemas.JobApplication, status_code=201)
def create_job(job: schemas.JobApplicationCreate, db: Session = Depends(get_db)):
    instance = models.JobApplication(
        title=job.title,
        company=job.company,
        date_applied=job.date_applied,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@app.get("/jobs", response_model=list[schemas.JobApplication])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(models.JobApplication).order_by(models.JobApplication.date_applied.desc()).all()


@app.post("/gmail/process")
def process_gmail():
    """
    Process Gmail for job application emails and save them to database.
    """
    try:
        results = process_gmail_applications()
        return {
            "success": True,
            "message": f"Processed {results['emails_processed']} emails, saved {results['applications_saved']} applications",
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing Gmail: {str(e)}",
            "results": None
        }
