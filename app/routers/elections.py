from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from typing import List
from .. import models, schemas
from ..dependencies import get_db, get_current_user, require_role

router = APIRouter(prefix="/elections", tags=["Elections"])


@router.get('/current', response_model=schemas.ElectionResponse)
def get_current_election(
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user),
):
    """Fetch the current election (upcoming or ongoing)."""
    now = datetime.utcnow()

    election = (
        db.query(models.Election)
        .filter(models.Election.end_date >= now)  # 👈 only require it's not already ended
        .order_by(models.Election.start_date.asc())
        .first()
    )
    if not election:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active or upcoming election found"
        )

    # Auto-compute status
    if election.start_date > now:
        computed_status = "upcoming"
    elif election.end_date < now:
        computed_status = "ended"
    else:
        computed_status = "active"

    # ❌ Don’t block upcoming elections
    if computed_status == "ended":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active election found"
        )

    # You can return election + computed status if needed
    return election


@router.post('/{election_id}/vote')
def cast_vote(
    election_id: int,
    payload: dict,  # expecting {"candidate_ids": [1, 2, ...]}
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user),
):
    """Cast vote(s) for one or more candidates"""
    # Only voters can vote
    if current_user.role != "voter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only voters can cast votes"
        )

    election = db.query(models.Election).filter(models.Election.id == election_id).first()
    if not election:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Election not found")

    now = datetime.utcnow()
    if not (election.start_date <= now <= election.end_date):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Election is not active")

    # Prevent double voting
    existing_vote = (
        db.query(models.Vote)
        .filter(models.Vote.user_id == current_user.id, models.Vote.election_id == election_id)
        .first()
    )
    if existing_vote:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already voted in this election")

    candidate_ids = payload.get("candidate_ids", [])
    if not candidate_ids or not isinstance(candidate_ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="candidate_ids must be a non-empty list")

    # Validate candidates
    valid_candidates = (
        db.query(models.Candidate)
        .filter(models.Candidate.id.in_(candidate_ids), models.Candidate.election_id == election_id)
        .all()
    )
    if len(valid_candidates) != len(candidate_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more candidates are invalid")

    # Record votes (one per candidate)
    receipt = f"VOTE-{datetime.utcnow().year}-{uuid4().hex[:10].upper()}"
    for cid in candidate_ids:
        vote = models.Vote(
            user_id=current_user.id,
            candidate_id=cid,
            election_id=election_id,
            receipt_id=receipt
        )
        db.add(vote)

    # Audit log
    audit = models.AuditLog(
        user_email=current_user.email,
        action="Submit Vote",
        status="success",
        details=f"Voted for candidates {candidate_ids} in election {election_id}"
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "receipt_id": receipt}


@router.get('/results/live', response_model=schemas.LiveResultsResponse)
def live_results(
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user),  # ✅ any logged-in user
):
    """Return live results (visible to voters, auditors, and admins)"""
    total = db.query(models.Vote).count()
    candidates = db.query(models.Candidate).all()

    data = {"totalVotes": total, "candidates": []}
    for c in candidates:
        data["candidates"].append({
            "candidateId": c.id,
            "name": c.name,
            "votes": len(c.votes),
            "position": c.position
        })
    return data



@router.get('/stats/voters')
def voter_stats(
    db: Session = Depends(get_db),
    current_user: schemas.UserResponse = Depends(require_role("admin")),
):
    """Return voter participation stats (restricted to admins + superadmins)"""
    total_voters = db.query(models.User).filter(models.User.role == "voter").count()
    total_votes_cast = db.query(models.Vote).count()
    return {"totalVoters": total_voters, "totalVotesCast": total_votes_cast}
