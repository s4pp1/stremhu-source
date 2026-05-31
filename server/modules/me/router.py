from fastapi import APIRouter, Depends, HTTPException, status
from modules.auth.dependencies import OptionalSessionGuard, SessionGuard
from modules.me.schemas import (
    MePreferenceCreateRequest,
    MePreferencesReorderRequest,
    MePreferenceUpdateRequest,
    MeUpdateRequest,
)
from modules.preferences.dependencies import get_user_preferences_service
from modules.preferences.enums import PreferenceEnum
from modules.preferences.schemas import Preference
from modules.preferences.user_service import UserPreferencesService
from modules.users.dependencies import get_users_service
from modules.users.models import UserModel
from modules.users.schemas import User, UserUpdateRequest
from modules.users.service import UsersService

router = APIRouter(prefix="/me", tags=["Me"])


@router.get("/", response_model=User | None)
def get(
    current_user: UserModel | None = Depends(OptionalSessionGuard()),
) -> UserModel | None:
    return current_user


@router.put("/", response_model=User)
def update(
    payload: MeUpdateRequest,
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> UserModel:
    """
    Updates the current user's profile information.
    """
    update_user_payload = UserUpdateRequest(
        username=payload.username,
        password=payload.password,
        torrent_seed=payload.torrent_seed,
        only_best_torrent=payload.only_best_torrent,
        role_id=None,
    )
    return users_service.update(current_user.id, update_user_payload)


@router.put("/api-key/regenerate", response_model=User)
def regenerate_api_key(
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> UserModel:
    """
    Regenerates the current user's API key.
    """
    return users_service.regenerate_token(current_user.id)


@router.get("/preferences", response_model=list[Preference])
def get_preferences(
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> list[Preference]:
    """
    Lists all of the current user's preference settings.
    """
    models = preferences_service.find(current_user.id)
    return [Preference.from_model(model) for model in models]


@router.post("/preferences", response_model=Preference)
def create_preference(
    payload: MePreferenceCreateRequest,
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> Preference:
    """
    Adds/creates a preference setting with ordered preferred attributes.
    """
    model = preferences_service.create(
        current_user.id, payload.preference, payload.preferred
    )
    return Preference.from_model(model)


@router.get("/preferences/{preference}", response_model=Preference)
def get_preference(
    preference: PreferenceEnum,
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> Preference:
    """
    Retrieves a specific preference setting for the current user.
    """
    model = preferences_service.find_one_by_preference(current_user.id, preference)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A(z) '{preference}' preferencia nem található.",
        )
    return Preference.from_model(model)


@router.post("/preferences/reorder", response_model=list[Preference])
def reorder_preferences(
    payload: MePreferencesReorderRequest,
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> list[Preference]:
    """
    Reorders the priority of preference categories.
    """
    models = preferences_service.reorder(current_user.id, payload.preferences)
    return [Preference.from_model(model) for model in models]


@router.put("/preferences/{preference}", response_model=Preference)
def update_preference(
    preference: PreferenceEnum,
    payload: MePreferenceUpdateRequest,
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> Preference:
    """
    Updates preferred attributes within an existing preference setting category.
    """
    model = preferences_service.update(
        current_user.id,
        preference,
        payload.preferred,
    )
    return Preference.from_model(model)


@router.delete("/preferences/{preference}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preference(
    preference: PreferenceEnum,
    preferences_service: UserPreferencesService = Depends(get_user_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> None:
    """
    Deletes a user's preference category setting.
    """
    preferences_service.delete_by_preference(current_user.id, preference)
