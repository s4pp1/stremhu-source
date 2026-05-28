from fastapi import APIRouter, Depends, HTTPException, status
from modules.auth.dependencies import SessionGuard
from modules.me.schemas import (
    ReorderPreferences,
    UserPreferenceCreate,
    UserPreferenceUpdate,
)
from modules.preferences.dependencies import get_user_preferences_service
from modules.preferences.enums import PreferenceEnum
from modules.preferences.schemas import Preference
from modules.preferences.user_service import UserPreferencesService
from modules.roles.enums import UserRole
from modules.users.dependencies import get_users_service
from modules.users.models import UserModel
from modules.users.schemas import CreateUser, UpdateUser, User
from modules.users.service import UsersService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=list[User],
)
def find(
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> list[UserModel]:
    return users_service.get_list()


@router.get(
    "/{user_id}",
    response_model=User,
)
def find_by_id(
    user_id: str,
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> UserModel:
    return users_service.get_by_id_or_raise(user_id)


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: CreateUser,
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> UserModel:
    return users_service.create(payload)


@router.put(
    "/{user_id}",
    response_model=User,
)
def update(
    user_id: str,
    payload: UpdateUser,
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> UserModel:
    return users_service.update(user_id, payload)


@router.put(
    "/{user_id}/token/regenerate",
    response_model=User,
)
def regenerate_token(
    user_id: str,
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> UserModel:
    return users_service.regenerate_token(user_id)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete(
    user_id: str,
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> None:
    users_service.delete(user_id, current_user)


# ─── User Preference Endpoints (Admin access) ───────────────────────


@router.get("/{user_id}/preferences", response_model=list[Preference])
def get_preferences(
    user_id: str,
    users_service: UsersService = Depends(get_users_service),
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> list[Preference]:
    """
    Lists all preferences for a specific user.
    """
    users_service.get_by_id_or_raise(user_id)
    models = preferences_service.find(user_id)
    return [Preference.from_model(model) for model in models]


@router.post("/{user_id}/preferences", response_model=Preference)
def create_preference(
    user_id: str,
    payload: UserPreferenceCreate,
    users_service: UsersService = Depends(get_users_service),
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> Preference:
    """
    Creates/adds a preference setting for a specific user.
    """
    users_service.get_by_id_or_raise(user_id)
    model = preferences_service.create(user_id, payload.preference, payload.preferred)
    return Preference.from_model(model)


@router.post("/{user_id}/preferences/reorder", response_model=list[Preference])
def reorder_preferences(
    user_id: str,
    payload: ReorderPreferences,
    users_service: UsersService = Depends(get_users_service),
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> list[Preference]:
    """
    Reorders the priority of preference categories for a specific user.
    """
    users_service.get_by_id_or_raise(user_id)
    models = preferences_service.reorder(user_id, payload.preferences)
    return [Preference.from_model(model) for model in models]


@router.get("/{user_id}/preferences/{preference}", response_model=Preference)
def get_preference(
    user_id: str,
    preference: PreferenceEnum,
    users_service: UsersService = Depends(get_users_service),
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> Preference:
    """
    Retrieves a specific preference setting for a specific user.
    """
    users_service.get_by_id_or_raise(user_id)
    model = preferences_service.find_one_by_preference(user_id, preference)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A(z) '{preference.value}' preferenciája nem található.",
        )
    return Preference.from_model(model)


@router.put("/{user_id}/preferences/{preference}", response_model=Preference)
def update_preference(
    user_id: str,
    preference: PreferenceEnum,
    payload: UserPreferenceUpdate,
    users_service: UsersService = Depends(get_users_service),
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> Preference:
    """
    Updates preferred attributes within an existing preference setting category for a specific user.
    """
    users_service.get_by_id_or_raise(user_id)
    model = preferences_service.update(
        user_id,
        preference,
        payload.preferred,
    )
    return Preference.from_model(model)


@router.delete(
    "/{user_id}/preferences/{preference}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_preference(
    user_id: str,
    preference: PreferenceEnum,
    users_service: UsersService = Depends(get_users_service),
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> None:
    """
    Deletes a specific preference category setting for a specific user.
    """
    users_service.get_by_id_or_raise(user_id)
    preferences_service.delete_by_preference(user_id, preference)
