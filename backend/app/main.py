from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_

from . import schemas, models
from .db import Base, engine, get_db
from .email_parser import process_gmail_applications
from .gemini_analyzer import is_gemini_available, gemini_analyzer

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
    # Check for duplicate before creating
    existing_job = db.query(models.JobApplication).filter(
        and_(
            models.JobApplication.title == job.title,
            models.JobApplication.company == job.company,
            models.JobApplication.date_applied == job.date_applied
        )
    ).first()
    
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job application with this title, company, and date already exists."
        )
    
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


@app.get("/jobs/{job_id}", response_model=schemas.JobApplication)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.JobApplication).filter(models.JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")
    return job


@app.put("/jobs/{job_id}", response_model=schemas.JobApplication)
def update_job(job_id: int, job_update: schemas.JobApplicationUpdate, db: Session = Depends(get_db)):
    job = db.query(models.JobApplication).filter(models.JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")
    
    # Update fields if provided
    if job_update.title is not None:
        job.title = job_update.title
    if job_update.company is not None:
        job.company = job_update.company
    if job_update.date_applied is not None:
        job.date_applied = job_update.date_applied
    if job_update.status is not None:
        job.status = job_update.status
    
    db.commit()
    db.refresh(job)
    return job


@app.patch("/jobs/{job_id}", response_model=schemas.JobApplication)
def update_job_status(job_id: int, job_update: schemas.JobApplicationUpdate, db: Session = Depends(get_db)):
    job = db.query(models.JobApplication).filter(models.JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")
    
    job.status = job_update.status
    db.commit()
    db.refresh(job)
    return job


@app.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.JobApplication).filter(models.JobApplication.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")
    
    db.delete(job)
    db.commit()
    return {"message": "Job application deleted successfully"}


@app.post("/gmail/process")
def process_gmail():
    """
    Process Gmail for job application emails and save them to database.
    """
    try:
        results = process_gmail_applications()
        return {
            "success": True,
            "message": f"Processed {results['emails_processed']} emails, saved {results['applications_saved']} new applications",
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing Gmail: {str(e)}",
            "results": None
        }


@app.post("/gmail/process-advanced")
def process_gmail_advanced(
    days_threshold: int = Query(7, description="Only analyze emails from the past N days", ge=1, le=365),
    use_gemini: bool = Query(True, description="Whether to use Gemini AI analysis"),
    max_results: int = Query(50, description="Maximum number of emails to process", ge=1, le=200)
):
    """
    Advanced Gmail processing with configurable parameters.
    
    - days_threshold: Only analyze emails from the past N days (1-365)
    - use_gemini: Whether to use Gemini AI analysis
    - max_results: Maximum number of emails to process
    """
    try:
        results = process_gmail_applications(
            days_threshold=days_threshold,
            use_gemini=use_gemini,
            max_results=max_results
        )
        
        return {
            "success": True,
            "message": f"Processed {results['emails_processed']} emails, saved {results['applications_saved']} new applications",
            "results": results,
            "settings": {
                "days_threshold": days_threshold,
                "use_gemini": use_gemini,
                "max_results": max_results
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing Gmail: {str(e)}",
            "results": None
        }


@app.get("/gemini/status")
def get_gemini_status():
    """
    Get Gemini API status and configuration.
    """
    try:
        stats = gemini_analyzer.get_usage_stats()
        return {
            "success": True,
            "gemini_status": stats,
            "recommendations": {
                "token_usage": "Configure days_threshold to control token usage",
                "free_tier": "Gemini 1.5 Flash is free with generous limits",
                "fallback": "System automatically falls back to regex parsing if Gemini unavailable"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting Gemini status: {str(e)}"
        }


@app.post("/gemini/test")
def test_gemini_analysis(
    subject: str = Query(..., description="Email subject to test"),
    body: str = Query(..., description="Email body to test"),
    from_email: str = Query("", description="Sender email address")
):
    """
    Test Gemini AI analysis on sample email content.
    """
    try:
        if not is_gemini_available():
            return {
                "success": False,
                "message": "Gemini API not available. Check your API key configuration.",
                "fallback_available": True
            }
        
        from .gemini_analyzer import analyze_email_with_gemini
        
        analysis_result = analyze_email_with_gemini(
            subject=subject,
            body=body,
            from_email=from_email
        )
        
        return {
            "success": True,
            "analysis": analysis_result,
            "token_estimate": gemini_analyzer.estimate_token_count(f"{subject}\n\n{body}")
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing Gemini analysis: {str(e)}"
        }
