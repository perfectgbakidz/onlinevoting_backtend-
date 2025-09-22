from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, database, dependencies, schemas

router = APIRouter(prefix="/auditor", tags=["Auditor"])


@router.get("/results/live", response_model=schemas.LiveResultsResponse)
def auditor_results(
    db: Session = Depends(database.get_db),
    current_user=Depends(dependencies.require_role("auditor")),
):
    election = (
        db.query(models.Election)
        .filter(models.Election.status == models.ElectionStatus.ongoing)
        .first()
    )
    if not election:
        raise HTTPException(status_code=404, detail="No ongoing election found")

    candidates = db.query(models.Candidate).filter(models.Candidate.election_id == election.id).all()
    total_votes = db.query(models.Vote).filter(models.Vote.election_id == election.id).count()

    return {
        "totalVotes": total_votes,
        "candidates": [
            {
                "candidateId": c.id,
                "name": c.name,
                "position": c.position,
                "votes": len(c.votes),
            }
            for c in candidates
        ],
    }
