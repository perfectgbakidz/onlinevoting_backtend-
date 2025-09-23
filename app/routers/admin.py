from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from .. import models, schemas, database, dependencies, auth
import shutil
import uuid
import os

router = APIRouter(prefix="/admin", tags=["Admin"])

UPLOAD_DIR = "uploads/candidates"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------- Helpers ----------------
def to_utc(dt: datetime) -> datetime:
    """Convert naive or tz-aware datetime to UTC-aware datetime."""
    if dt.tzinfo is None:  # assume naive -> treat as local time
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_election_status(election: models.Election) -> str:
    """Compute status based on UTC-aware datetimes."""
    now = datetime.now(timezone.utc)  # tz-aware UTC
    if election.start_date > now:
        return "upcoming"
    elif election.end_date < now:
        return "ended"
    return "active"


# ---------------- Dashboard ----------------
@router.get("/overview")
def overview(
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    total_votes = db.query(models.Vote).count()
    active = db.query(models.Election).filter(models.Election.status == "active").count()
    completed = db.query(models.Election).filter(models.Election.status == "ended").count()
    results = (
        db.query(models.Candidate)
        .join(models.Vote, models.Candidate.id == models.Vote.candidate_id, isouter=True)
        .all()
    )
    return {
        "stats": {"totalVotes": total_votes, "activeElections": active, "completedElections": completed},
        "results": results,
    }


# ---------------- Election Management ----------------
@router.post("/elections", response_model=schemas.ElectionResponse, status_code=status.HTTP_201_CREATED)
def create_election(
    election_in: schemas.ElectionCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    # Force UTC storage
    start_utc = to_utc(election_in.start_date)
    end_utc = to_utc(election_in.end_date)

    ev = models.Election(
        title=election_in.title,
        start_date=start_utc,
        end_date=end_utc,
    )
    ev.status = get_election_status(ev)

    db.add(ev)
    db.commit()
    db.refresh(ev)

    audit = models.AuditLog(
        user_email=current_user.email,
        action="Create Election",
        status="success",
        details=f"Created election {ev.title}"
    )
    db.add(audit)
    db.commit()
    return ev


@router.put("/elections/{election_id}", response_model=schemas.ElectionResponse)
def update_election(
    election_id: int,
    election_in: schemas.ElectionUpdate,
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    election = db.query(models.Election).filter(models.Election.id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    if election_in.title:
        election.title = election_in.title
    if election_in.start_date:
        election.start_date = to_utc(election_in.start_date)
    if election_in.end_date:
        election.end_date = to_utc(election_in.end_date)

    # Always recompute status
    election.status = get_election_status(election)

    db.commit()
    db.refresh(election)

    audit = models.AuditLog(
        user_email=current_user.email,
        action="Update Election",
        status="success",
        details=f"Updated election {election.id}"
    )
    db.add(audit)
    db.commit()
    return election


# ---------------- Candidate Management ----------------
@router.post("/elections/{election_id}/candidates", response_model=schemas.CandidateResponse, status_code=status.HTTP_201_CREATED)
def add_candidate(
    election_id: int,
    name: str = Form(...),
    level: str = Form(...),
    position: str = Form(...),
    manifesto: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    election = db.query(models.Election).filter(models.Election.id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    filename = f"{uuid.uuid4().hex}_{photo.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    candidate = models.Candidate(
        election_id=election_id,
        name=name,
        level=level,
        position=position,
        manifesto=manifesto,
        photo_url=filepath,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    audit = models.AuditLog(
        user_email=current_user.email,
        action="Add Candidate",
        status="success",
        details=f"Added candidate {candidate.name} to election {election_id}"
    )
    db.add(audit)
    db.commit()
    return candidate


# ---------------- Auditor Management ----------------
@router.get("/auditors", response_model=List[schemas.UserResponse])
def list_auditors(
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    return db.query(models.User).filter(models.User.role == "auditor").all()


@router.post("/auditors", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_auditor(
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = auth.get_password_hash(user_in.password)
    auditor = models.User(name=user_in.name, email=user_in.email, hashed_password=hashed, role="auditor")
    db.add(auditor)
    db.commit()
    db.refresh(auditor)

    audit = models.AuditLog(
        user_email=current_user.email,
        action="Create Auditor",
        status="success",
        details=f"Created auditor {auditor.email}"
    )
    db.add(audit)
    db.commit()
    return auditor


@router.get("/elections", response_model=List[schemas.ElectionResponse])
def list_elections(
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    elections = db.query(models.Election).all()
    # Auto-compute status for consistency
    for e in elections:
        e.status = get_election_status(e)
    return elections


@router.delete("/auditors/{auditor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_auditor(
    auditor_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("admin", "superadmin"))
):
    auditor = db.query(models.User).filter(models.User.id == auditor_id, models.User.role == "auditor").first()
    if not auditor:
        raise HTTPException(status_code=404, detail="Auditor not found")

    db.delete(auditor)
    db.commit()

    audit = models.AuditLog(
        user_email=current_user.email,
        action="Delete Auditor",
        status="success",
        details=f"Deleted auditor {auditor.email}"
    )
    db.add(audit)
    db.commit()
    return None
