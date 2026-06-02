from fastapi import APIRouter, Depends, HTTPException, status
from modules.auth.dependencies import SessionGuard
from modules.preferences.schemas import Preference
from modules.roles.enums import UserRole
from modules.user_preference_definitions.dependencies import (
    get_user_preference_definitions_service,
)
from modules.user_preference_definitions.models import UserPreferenceDefinitionModel
from modules.user_preference_definitions.service import UserPreferenceDefinitionsService
from modules.users.dependencies import get_users_service
from modules.users.models import UserModel
from modules.users.schemas.api import (
    User,
    UserCreateRequest,
    UserPreferenceCreateRequest,
    UserPreferencesReorderRequest,
    UserPreferenceUpdateRequest,
    UserUpdateRequest,
)
from modules.users.service import UsersService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=list[User],
)
def get_list(
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> list[UserModel]:
    return users_service.get_list()


@router.get(
    "/{user_id}",
    response_model=User,
)
def get(
    user_id: str,
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> UserModel:
    return users_service.get_by_id(user_id)


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: UserCreateRequest,
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
    payload: UserUpdateRequest,
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> UserModel:
    return users_service.update(user_id, payload)


@router.put(
    "/{user_id}/api_key/regenerate",
    response_model=User,
)
def regenerate_api_key(
    user_id: str,
    users_service: UsersService = Depends(get_users_service),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> UserModel:
    return users_service.regenerate_api_key(user_id)


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


@router.get("/{user_id}/preferences", response_model=list[Preference])
def get_preferences(
    user_id: str,
    users_service: UsersService = Depends(get_users_service),
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> list[UserPreferenceDefinitionModel]:
    """
    Lists all preferences for a specific user.
    """
    users_service.get_by_id(user_id)
    return user_preference_definitions_service.find_list(user_id)


@router.post("/{user_id}/preferences", response_model=Preference)
def create_preference(
    user_id: str,
    payload: UserPreferenceCreateRequest,
    users_service: UsersService = Depends(get_users_service),
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> Preference:
    """
    Creates/adds a preference setting for a specific user.
    """
    users_service.get_by_id(user_id)
    model = user_preference_definitions_service.create(
        user_id,
        payload.preference_id,
        payload.attribute_ids,
    )
    return Preference.from_model(model)


@router.post("/{user_id}/preferences/reorder", response_model=list[Preference])
def reorder_preferences(
    user_id: str,
    payload: UserPreferencesReorderRequest,
    users_service: UsersService = Depends(get_users_service),
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> list[Preference]:
    """
    Reorders the priority of preference categories for a specific user.
    """
    users_service.get_by_id(user_id)
    models = user_preference_definitions_service.reorder(
        user_id, payload.preference_ids
    )
    return [Preference.from_model(model) for model in models]


@router.get("/{user_id}/preferences/{preference_id}", response_model=Preference)
def get_preference(
    user_id: str,
    preference_id: str,
    users_service: UsersService = Depends(get_users_service),
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> Preference:
    """
    Retrieves a specific preference setting for a specific user.
    """
    users_service.get_by_id(user_id)
    model = user_preference_definitions_service.find_by_id(user_id, preference_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A(z) '{preference_id}' preferenciája nem található.",
        )
    return Preference.from_model(model)


@router.put("/{user_id}/preferences/{preference_id}", response_model=Preference)
def update_preference(
    user_id: str,
    preference_id: str,
    payload: UserPreferenceUpdateRequest,
    users_service: UsersService = Depends(get_users_service),
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> Preference:
    """
    Updates preferred attributes within an existing preference setting category for a specific user.
    """
    users_service.get_by_id(user_id)
    model = user_preference_definitions_service.update(
        user_id,
        preference_id,
        payload.attribute_ids,
    )
    return Preference.from_model(model)


@router.delete(
    "/{user_id}/preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_preference(
    user_id: str,
    preference_id: str,
    users_service: UsersService = Depends(get_users_service),
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    _: UserModel = Depends(SessionGuard([UserRole.ADMIN])),
) -> None:
    """
    Deletes a specific preference category setting for a specific user.
    """
    users_service.get_by_id(user_id)
    user_preference_definitions_service.delete(user_id, preference_id)
