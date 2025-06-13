from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.models.schemas import UserHistory, SymptomLog, UpdateResolutionRequest
from app.services.database import db_service
from app.api.routes.auth import get_current_user_id

router = APIRouter()

@router.get("/", response_model=UserHistory)
async def get_user_history(
    limit: int = 10,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's symptom history"""
    try:
        logs = await db_service.get_user_history(current_user_id, limit)
        
        return UserHistory(
            logs=logs,
            total_count=len(logs)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")

@router.get("/recent")
async def get_recent_symptoms(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get recent symptoms for quick access/re-submission"""  
    try:
        recent_symptoms = await db_service.get_recent_user_symptoms(current_user_id, limit=5)
        
        return {
            "recent_symptoms": recent_symptoms
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve recent symptoms: {str(e)}")

@router.get("/stats")
async def get_user_stats(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's health statistics and trends"""
    try:
        logs = await db_service.get_user_history(current_user_id, limit=50)
        
        # Calculate basic stats
        total_assessments = len(logs)
        urgency_counts = {}
        
        for log in logs:
            urgency_level = log.urgency_level.value
            urgency_counts[urgency_level] = urgency_counts.get(urgency_level, 0) + 1
        
        most_common_urgency = max(urgency_counts, key=urgency_counts.get) if urgency_counts else None
        
        return {
            "total_assessments": total_assessments,
            "urgency_distribution": urgency_counts,
            "most_common_urgency": most_common_urgency,
            "recent_activity": len([log for log in logs[:10]])  # Last 10 assessments
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")

@router.put("/resolution")
async def update_resolution_status(
    request: UpdateResolutionRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update the resolution status of a symptom"""
    try:
        result = await db_service.update_resolution_status(
            symptom_log_id=request.symptom_log_id,
            resolution_status=request.resolution_status.value,
            user_id=current_user_id
        )
        
        return {
            "success": True,
            "message": f"Resolution status updated to {request.resolution_status.value}",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update resolution status: {str(e)}")

@router.get("/unresolved")
async def get_unresolved_symptoms(
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's unresolved symptoms"""
    try:
        unresolved_symptoms = await db_service.get_unresolved_symptoms(current_user_id, limit=10)
        
        return {
            "unresolved_symptoms": unresolved_symptoms,
            "count": len(unresolved_symptoms)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve unresolved symptoms: {str(e)}") 