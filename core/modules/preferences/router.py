from typing import Annotated

from fastapi import APIRouter, Depends

from core.modules.preferences.dependencies import get_preferences_service
from core.modules.preferences.models import PreferenceModel
from core.modules.preferences.schemas.api import PreferenceResponse
from core.modules.preferences.service import PreferencesService

router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"],
)


@router.get(
    "/",
    response_model=list[PreferenceResponse],
)
def get_all(
    preferences_service: Annotated[
        PreferencesService, Depends(get_preferences_service)
    ],
) -> list[PreferenceModel]:
    return preferences_service.get_list()


@router.get(
    "/{preference_id}",
    response_model=PreferenceResponse,
)
def get(
    preference_id: str,
    preferences_service: Annotated[
        PreferencesService, Depends(get_preferences_service)
    ],
):
    return preferences_service.get_by_id(preference_id)
