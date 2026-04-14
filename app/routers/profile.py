"""Profile router for user profile CRUD operations."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.dependencies.auth import get_current_user
from app.schemas.profile import ProfileUpdate, ProfileResponse, ProfilePublic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("/", response_model=ProfileResponse, summary="Obtener perfil del usuario")
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get the current user's profile.
    """
    return ProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        preferences=current_user.preferences or {},
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.put("/", response_model=ProfileResponse, summary="Actualizar perfil y preferencias")
async def update_profile(
    profile_data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the current user's profile.
    """
    try:
        if profile_data.first_name is not None:
            current_user.first_name = profile_data.first_name
        if profile_data.last_name is not None:
            current_user.last_name = profile_data.last_name
        if profile_data.preferences is not None:
            # Merge with existing preferences to avoid completely overwriting if we just send part of it
            current_prefs = current_user.preferences or {}
            current_user.preferences = {**current_prefs, **profile_data.preferences}
            
        db.add(current_user)
        # Commit handled by get_db
        
        logger.info(f"Profile updated for user: {current_user.id}")
        return ProfileResponse(
            id=str(current_user.id),
            email=current_user.email,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            preferences=current_user.preferences or {},
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error updating profile for {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating profile"
        )

@router.delete("/", response_model=dict, summary="Eliminar cuenta del usuario")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete the current user's account.
    """
    try:
        await db.delete(current_user)
        logger.warning(f"Account deletion for user: {current_user.id}")
        
        return {
            "message": "Account deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting account for {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting account"
        )
