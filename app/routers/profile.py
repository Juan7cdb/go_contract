"""Profile router for user profile CRUD operations."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends

from app.core.client import get_supabase_client
from app.dependencies.auth import get_current_user, TokenPayload
from app.schemas.profile import ProfileUpdate, ProfileResponse, ProfilePublic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/", response_model=ProfileResponse)
async def get_profile(current_user: TokenPayload = Depends(get_current_user)):
    """
    Get the current user's profile.
    
    Returns the full profile data for the authenticated user.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("profiles").select("*").eq("id", current_user.sub).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        return ProfileResponse(**response.data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile for {current_user.sub}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching profile"
        )


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Update the current user's profile.
    
    Updates only the provided fields. Omitted fields remain unchanged.
    """
    supabase = get_supabase_client()
    
    try:
        # Filter out None values to only update provided fields
        update_data = {k: v for k, v in profile_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        response = supabase.table("profiles").update(update_data).eq("id", current_user.sub).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        logger.info(f"Profile updated for user: {current_user.sub}")
        return ProfileResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile for {current_user.sub}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating profile"
        )


@router.delete("/", response_model=dict)
async def delete_account(current_user: TokenPayload = Depends(get_current_user)):
    """
    Delete the current user's account.
    
    This permanently deletes the user's profile.
    This action cannot be undone.
    """
    supabase = get_supabase_client()
    
    try:
        # Delete profile
        supabase.table("profiles").delete().eq("id", current_user.sub).execute()
        
        logger.warning(f"Account deletion requested for user: {current_user.sub}")
        
        return {
            "message": "Account deleted successfully",
            "note": "Please contact support if you need to fully remove your authentication data"
        }
        
    except Exception as e:
        logger.error(f"Error deleting account for {current_user.sub}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting account"
        )


@router.get("/{user_id}", response_model=ProfilePublic)
async def get_profile_by_id(
    user_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Get a user's public profile by ID.
    
    Returns limited public profile information for another user.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("profiles").select(
            "id, first_name, last_name"
        ).eq("id", user_id).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        return ProfilePublic(**response.data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching profile"
        )
