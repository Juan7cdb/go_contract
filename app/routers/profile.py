"""Profile router for user profile CRUD operations."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.dependencies.auth import get_current_user
from app.schemas.profile import ProfileUpdate, ProfileResponse, ProfilePublic
from app.services.storage_service import (
    get_storage_service,
    StorageService,
    StorageError,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Profile"])


def _build_profile_response(user: User, storage: StorageService) -> ProfileResponse:
    return ProfileResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=storage.generate_avatar_url(user.avatar_key),
        preferences=user.preferences or {},
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get(
    "/",
    response_model=ProfileResponse,
    response_model_exclude_none=True,
    response_model_by_alias=True,
    summary="Obtener perfil del usuario",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Get the current user's profile."""
    return _build_profile_response(current_user, storage)


@router.put(
    "/",
    response_model=ProfileResponse,
    response_model_exclude_none=True,
    response_model_by_alias=True,
    summary="Actualizar perfil y preferencias",
)
async def update_profile(
    profile_data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Update the current user's profile."""
    try:
        if profile_data.first_name is not None:
            current_user.first_name = profile_data.first_name
        if profile_data.last_name is not None:
            current_user.last_name = profile_data.last_name
        if profile_data.preferences is not None:
            current_prefs = current_user.preferences or {}
            # `exclude_unset=True` (not `exclude_none=True`) so clients can
            # explicitly clear a preference by sending its value as `null` —
            # `exclude_none` would silently drop the key and the merge would
            # keep the previously persisted value forever.
            # `by_alias=True` keeps the merged dict in camelCase on disk,
            # matching the existing JSON column shape (frontend payload).
            prefs_dict = profile_data.preferences.model_dump(
                by_alias=True, exclude_unset=True
            )
            current_user.preferences = {**current_prefs, **prefs_dict}

        db.add(current_user)

        logger.info(f"Profile updated for user: {current_user.id}")
        return _build_profile_response(current_user, storage)

    except Exception as e:
        logger.error(f"Error updating profile for {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating profile",
        )


@router.post("/avatar", response_model=ProfileResponse, summary="Subir foto de perfil")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Upload (or replace) the current user's profile picture."""
    previous_key = current_user.avatar_key
    try:
        new_key = await storage.upload_avatar(current_user.id, file)
    except StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected avatar upload error for {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading avatar",
        )

    current_user.avatar_key = new_key
    db.add(current_user)

    if previous_key and previous_key != new_key:
        storage.delete_avatar(previous_key)

    logger.info(f"Avatar updated for user {current_user.id}")
    return _build_profile_response(current_user, storage)


@router.delete("/avatar", response_model=ProfileResponse, summary="Eliminar foto de perfil")
async def delete_avatar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Remove the current user's profile picture."""
    previous_key = current_user.avatar_key
    if previous_key:
        storage.delete_avatar(previous_key)
        current_user.avatar_key = None
        db.add(current_user)
        logger.info(f"Avatar removed for user {current_user.id}")

    return _build_profile_response(current_user, storage)


@router.delete("/", response_model=dict, summary="Eliminar cuenta del usuario")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Delete the current user's account."""
    try:
        if current_user.avatar_key:
            storage.delete_avatar(current_user.avatar_key)
        await db.delete(current_user)
        logger.warning(f"Account deletion for user: {current_user.id}")

        return {"message": "Account deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting account for {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting account",
        )
