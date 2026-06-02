from fastapi import APIRouter, Depends, HTTPException, status
from modules.auth.dependencies import OptionalSessionGuard, SessionGuard
from modules.me.schemas import (
    MePreferenceCreateRequest,
    MePreferencesReorderRequest,
    MePreferenceUpdateRequest,
    MeUpdateRequest,
)
from modules.preferences.schemas import Preference
from modules.user_preference_definitions.dependencies import (
    get_user_preference_definitions_service,
)
from modules.user_preference_definitions.service import UserPreferenceDefinitionsService
from modules.users.dependencies import get_users_service
from modules.users.models import UserModel
from modules.users.schemas.api import UserResponse
from modules.users.schemas.internal import UserUpdate
from modules.users.service import UsersService

router = APIRouter(prefix="/me", tags=["Me"])


@router.get("/", response_model=UserResponse | None)
def get(
    current_user: UserModel | None = Depends(OptionalSessionGuard()),
) -> UserModel | None:
    return current_user


@router.put("/", response_model=UserResponse)
def update(
    payload: MeUpdateRequest,
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> UserModel:
    """
    Updates the current user's profile information.
    """
    update_user_payload = UserUpdate(
        username=payload.username,
        password=payload.password,
        torrent_seed=payload.torrent_seed,
        only_best_torrent=payload.only_best_torrent,
        role_id=None,
    )
    return users_service.update(current_user.id, update_user_payload)


@router.put("/api-key/regenerate", response_model=UserResponse)
def regenerate_api_key(
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> UserModel:
    """
    Regenerates the current user's API key.
    """
    return users_service.regenerate_api_key(current_user.id)


@router.get("/preferences", response_model=list[Preference])
def get_preferences(
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> list[Preference]:
    """
    Lists all of the current user's preference settings.
    """
    models = user_preference_definitions_service.find_list(current_user.id)
    return [Preference.from_model(model) for model in models]


@router.post("/preferences", response_model=Preference)
def create_preference(
    payload: MePreferenceCreateRequest,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> Preference:
    """
    Adds/creates a preference setting with ordered preferred attributes.
    """
    model = user_preference_definitions_service.create(
        current_user.id,
        payload.preference_id,
        payload.preferred,
    )
    return Preference.from_model(model)


@router.get("/preferences/{preference_id}", response_model=Preference)
def get_preference(
    preference_id: str,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> Preference:
    """
    Retrieves a specific preference setting for the current user.
    """
    model = user_preference_definitions_service.find_by_id(
        current_user.id, preference_id
    )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A(z) '{preference_id}' preferencia nem található.",
        )
    return Preference.from_model(model)


@router.post("/preferences/reorder", response_model=list[Preference])
def reorder_preferences(
    payload: MePreferencesReorderRequest,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> list[Preference]:
    """
    Reorders the priority of preference categories.
    """
    models = user_preference_definitions_service.reorder(
        current_user.id, payload.preference_ids
    )
    return [Preference.from_model(model) for model in models]


@router.put("/preferences/{preference_id}", response_model=Preference)
def update_preference(
    preference_id: str,
    payload: MePreferenceUpdateRequest,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> Preference:
    """
    Updates preferred attributes within an existing preference setting category.
    """
    model = user_preference_definitions_service.update(
        current_user.id,
        preference_id,
        payload.preferred,
    )
    return Preference.from_model(model)


@router.delete("/preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preference(
    preference_id: str,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> None:
    """
    Deletes a user's preference category setting.
    """
    user_preference_definitions_service.delete(current_user.id, preference_id)
