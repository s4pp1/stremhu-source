from fastapi import APIRouter, Depends, HTTPException, status
from modules.attribute_exclusions.dependencies import get_attribute_exclusions_service
from modules.attribute_exclusions.schemas.api import AttributeExclusionCreateRequest
from modules.attribute_exclusions.service import AttributeExclusionsService
from modules.attributes.schemas.api import AttributeResponse
from modules.auth.dependencies import OptionalSessionGuard, SessionGuard
from modules.me.schemas.api import (
    MeUpdateRequest,
)
from modules.preferences.dependencies import get_preferences_service
from modules.preferences.schemas.api import (
    PreferenceCreateRequest,
    PreferenceResponse,
    PreferencesReorderRequest,
    PreferenceUpdateRequest,
)
from modules.preferences.service import PreferencesService
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
    update_payload = payload.model_dump(exclude_unset=True)
    user_update = UserUpdate(**update_payload)

    return users_service.update(current_user.id, user_update)


@router.put("/api-key/regenerate", response_model=UserResponse)
def regenerate_api_key(
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
) -> UserModel:
    return users_service.regenerate_api_key(current_user.id)


# --- ME PREFERENCES ---


@router.get(
    "/preferences/",
    response_model=list[PreferenceResponse],
)
def get_preferences(
    preferences_service: PreferencesService = Depends(get_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
):
    models = preferences_service.get_list(user_id=current_user.id)
    return models


@router.get(
    "/preferences/{preference_id}",
    response_model=PreferenceResponse,
)
def get_preference(
    preference_id: str,
    preferences_service: PreferencesService = Depends(get_preferences_service),
    current_user: UserModel = Depends(SessionGuard()),
):
    model = preferences_service.get_by_id(id=preference_id, user_id=current_user.id)
    return model


# --- ME PREFERENCE DEFINITIONS ---


@router.get(
    "/preferences/definitions/",
    response_model=list[PreferenceResponse],
)
def get_preference_definitions(
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> list[PreferenceResponse]:
    models = user_preference_definitions_service.find_list(current_user.id)
    return [
        PreferenceResponse.from_user_preference_definition_model(model)
        for model in models
    ]


@router.post(
    "/preferences/definitions/",
    response_model=PreferenceResponse,
)
def create_preference_definition(
    payload: PreferenceCreateRequest,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> PreferenceResponse:
    model = user_preference_definitions_service.create(
        current_user.id,
        payload,
    )
    return PreferenceResponse.from_user_preference_definition_model(model)


@router.put(
    "/preferences/definitions/reorder",
    response_model=list[PreferenceResponse],
)
def reorder_preference_definitions(
    payload: PreferencesReorderRequest,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> list[PreferenceResponse]:
    models = user_preference_definitions_service.reorder(
        current_user.id, payload.preference_ids
    )
    return [
        PreferenceResponse.from_user_preference_definition_model(model)
        for model in models
    ]


@router.get(
    "/preferences/definitions/{preference_id}",
    response_model=PreferenceResponse,
)
def get_preference_definition(
    preference_id: str,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> PreferenceResponse:
    model = user_preference_definitions_service.find_by_id(
        current_user.id, preference_id
    )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A(z) '{preference_id}' preferencia nem található.",
        )
    return PreferenceResponse.from_user_preference_definition_model(model)


@router.put(
    "/preferences/definitions/{preference_id}",
    response_model=PreferenceResponse,
)
def update_preference_definition(
    preference_id: str,
    payload: PreferenceUpdateRequest,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> PreferenceResponse:
    model = user_preference_definitions_service.update(
        current_user.id,
        preference_id,
        payload,
    )
    return PreferenceResponse.from_user_preference_definition_model(model)


@router.delete(
    "/preferences/definitions/{preference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_preference_definition(
    preference_id: str,
    user_preference_definitions_service: UserPreferenceDefinitionsService = Depends(
        get_user_preference_definitions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
) -> None:
    user_preference_definitions_service.delete(current_user.id, preference_id)


# --- ME ATTRIBUTES ---


@router.get(
    "/attributes/",
    response_model=list[AttributeResponse],
)
def get_attributes(
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
):
    models = users_service.get_attributes(user_id=current_user.id)
    return models


# --- ME ATTRIBUTE EXCLUSIONS ---


@router.get(
    "/attributes/exclusions/",
    response_model=list[AttributeResponse],
)
def get_attribute_exclusions(
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
):
    models = users_service.get_attribute_exclusions(
        user_id=current_user.id,
    )
    return [AttributeResponse.from_attribute_exclusion_model(model) for model in models]


@router.post(
    "/attributes/exclusions/",
    response_model=AttributeResponse,
)
def create_attribute_exclusion(
    payload: AttributeExclusionCreateRequest,
    users_service: UsersService = Depends(get_users_service),
    current_user: UserModel = Depends(SessionGuard()),
):
    model = users_service.create_attribute_exclusion(
        user_id=current_user.id,
        payload=payload,
    )
    return AttributeResponse.from_attribute_exclusion_model(model)


@router.delete(
    "/attributes/exclusions/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_attribute_exclusion(
    attribute_id: str,
    attribute_exclusions_service: AttributeExclusionsService = Depends(
        get_attribute_exclusions_service
    ),
    current_user: UserModel = Depends(SessionGuard()),
):
    attribute_exclusions_service.delete(
        attribute_id=attribute_id,
        user_id=current_user.id,
    )
    return None
