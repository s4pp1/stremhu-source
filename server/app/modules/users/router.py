from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.attribute_exclusions.dependencies import (
    get_attribute_exclusions_service,
)
from app.modules.attribute_exclusions.schemas.api import AttributeExclusionCreateRequest
from app.modules.attribute_exclusions.service import AttributeExclusionsService
from app.modules.attributes.schemas.api import AttributeResponse
from app.modules.auth.dependencies import SessionGuard
from app.modules.preferences.dependencies import get_preferences_service
from app.modules.preferences.schemas.api import (
    PreferenceCreateRequest,
    PreferenceResponse,
    PreferencesReorderRequest,
    PreferenceUpdateRequest,
)
from app.modules.preferences.service import PreferencesService
from app.modules.roles.constants import UserRoleKey
from app.modules.user_preference_definitions.dependencies import (
    get_user_preference_definitions_service,
)
from app.modules.user_preference_definitions.service import (
    UserPreferenceDefinitionsService,
)
from app.modules.users.dependencies import get_users_service
from app.modules.users.models import UserModel
from app.modules.users.schemas.api import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.modules.users.service import UsersService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=list[UserResponse],
)
def get_list(
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> list[UserModel]:
    return users_service.get_list()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: UserCreateRequest,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> UserModel:
    return users_service.create(payload)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get(
    user_id: str,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> UserModel:
    return users_service.get_by_id(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
)
def update(
    user_id: str,
    payload: UserUpdateRequest,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> UserModel:
    return users_service.update(user_id, payload)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete(
    user_id: str,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    current_user: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> None:
    users_service.delete(user_id, current_user)


@router.put(
    "/{user_id}/api_key/regenerate",
    response_model=UserResponse,
)
def regenerate_api_key(
    user_id: str,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> UserModel:
    return users_service.regenerate_api_key(user_id)


# --- USER PREFERENCES ---


@router.get(
    "/{user_id}/preferences/",
    response_model=list[PreferenceResponse],
)
def get_preferences(
    user_id: str,
    preferences_service: Annotated[
        PreferencesService, Depends(get_preferences_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    models = preferences_service.get_list(user_id=user_id)
    return models


@router.get(
    "/{user_id}/preferences/{preference_id}",
    response_model=PreferenceResponse,
)
def get_preference(
    user_id: str,
    preference_id: str,
    preferences_service: Annotated[
        PreferencesService, Depends(get_preferences_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    model = preferences_service.get_by_id(
        id=preference_id,
        user_id=user_id,
    )
    return model


# --- USER PREFERENCE DEFINITIONS ---


@router.get(
    "/{user_id}/preferences/definitions/",
    response_model=list[PreferenceResponse],
)
def get_preference_definitions(
    user_id: str,
    user_preference_definitions_service: Annotated[
        UserPreferenceDefinitionsService,
        Depends(get_user_preference_definitions_service),
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    models = user_preference_definitions_service.find_list(user_id)
    return [
        PreferenceResponse.from_user_preference_definition_model(model)
        for model in models
    ]


@router.post(
    "/{user_id}/preferences/definitions/",
    response_model=PreferenceResponse,
)
def create_preference_definition(
    user_id: str,
    payload: PreferenceCreateRequest,
    user_preference_definitions_service: Annotated[
        UserPreferenceDefinitionsService,
        Depends(get_user_preference_definitions_service),
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> PreferenceResponse:
    model = user_preference_definitions_service.create(
        user_id,
        payload,
    )
    return PreferenceResponse.from_user_preference_definition_model(model)


@router.put(
    "/{user_id}/preferences/definitions/reorder",
    response_model=list[PreferenceResponse],
)
def reorder_preference_definitions(
    user_id: str,
    payload: PreferencesReorderRequest,
    user_preference_definitions_service: Annotated[
        UserPreferenceDefinitionsService,
        Depends(get_user_preference_definitions_service),
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> list[PreferenceResponse]:
    models = user_preference_definitions_service.reorder(
        user_id, payload.preference_ids
    )
    return [
        PreferenceResponse.from_user_preference_definition_model(model)
        for model in models
    ]


@router.get(
    "/{user_id}/preferences/definitions/{preference_id}",
    response_model=PreferenceResponse,
)
def get_preference_definition(
    user_id: str,
    preference_id: str,
    user_preference_definitions_service: Annotated[
        UserPreferenceDefinitionsService,
        Depends(get_user_preference_definitions_service),
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> PreferenceResponse:
    model = user_preference_definitions_service.get_by_id(user_id, preference_id)
    return PreferenceResponse.from_user_preference_definition_model(model)


@router.put(
    "/{user_id}/preferences/definitions/{preference_id}",
    response_model=PreferenceResponse,
)
def update_preference_definition(
    user_id: str,
    preference_id: str,
    payload: PreferenceUpdateRequest,
    user_preference_definitions_service: Annotated[
        UserPreferenceDefinitionsService,
        Depends(get_user_preference_definitions_service),
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> PreferenceResponse:
    model = user_preference_definitions_service.update(
        user_id,
        preference_id,
        payload,
    )
    return PreferenceResponse.from_user_preference_definition_model(model)


@router.delete(
    "/{user_id}/preferences/definitions/{preference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_preference_definition(
    user_id: str,
    preference_id: str,
    user_preference_definitions_service: Annotated[
        UserPreferenceDefinitionsService,
        Depends(get_user_preference_definitions_service),
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
) -> None:
    user_preference_definitions_service.delete(user_id, preference_id)


@router.get(
    "/{user_id}/attributes/",
    response_model=list[AttributeResponse],
)
def get_attributes(
    user_id: str,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    models = users_service.get_attributes(user_id=user_id)
    return models


# --- USER ATTRIBUTE EXCLUSIONS ---


@router.get(
    "/{user_id}/attributes/exclusions/",
    response_model=list[AttributeResponse],
)
def get_attribute_exclusions(
    user_id: str,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    models = users_service.get_attribute_exclusions(
        user_id=user_id,
    )
    return [AttributeResponse.from_attribute_exclusion_model(model) for model in models]


@router.post(
    "/{user_id}/attributes/exclusions/",
    response_model=AttributeResponse,
)
def create_attribute_exclusion(
    user_id: str,
    payload: AttributeExclusionCreateRequest,
    users_service: Annotated[UsersService, Depends(get_users_service)],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    model = users_service.create_attribute_exclusion(
        user_id=user_id,
        payload=payload,
    )
    return AttributeResponse.from_attribute_exclusion_model(model)


@router.delete(
    "/{user_id}/attributes/exclusions/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_attribute_exclusion(
    user_id: str,
    attribute_id: str,
    attribute_exclusions_service: Annotated[
        AttributeExclusionsService, Depends(get_attribute_exclusions_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    attribute_exclusions_service.delete(
        attribute_id=attribute_id,
        user_id=user_id,
    )
    return None
