from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.models.schemas import SymptomInput
from app.services.triage import triage_service
from app.api.routes.auth import get_current_user_id

router = APIRouter()

@router.post("/assess", response_model=Dict[str, Any])
async def assess_symptoms(
    symptoms: Dict[str, str],
    current_user_id: str = Depends(get_current_user_id)
):
    """Process symptom assessment and return triage recommendation"""
    try:
        if not symptoms.get("symptoms"):
            raise HTTPException(status_code=400, detail="Symptoms are required")
        
        result = await triage_service.assess_symptoms(
            user_id=current_user_id,
            symptoms=symptoms["symptoms"]
        )
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage assessment failed: {str(e)}")

@router.get("/urgency-levels")
async def get_urgency_levels():
    """Get available urgency levels and their descriptions"""
    return {
        "urgency_levels": {
            "Emergency": {
                "description": "Life-threatening conditions requiring immediate ER visit",
                "color": "#DC2626",
                "priority": 5
            },
            "Urgent": {
                "description": "Serious conditions requiring same-day medical attention",
                "color": "#EA580C",
                "priority": 4
            },
            "Primary Care": {
                "description": "Non-urgent conditions suitable for routine doctor visit",
                "color": "#D97706",
                "priority": 3
            },
            "Telehealth": {
                "description": "Minor conditions that can be addressed via remote consultation",
                "color": "#059669",
                "priority": 2
            },
            "Self-Care": {
                "description": "Minor conditions manageable with home care",
                "color": "#0284C7",
                "priority": 1
            }
        }
    } 