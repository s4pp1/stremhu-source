from fastapi import APIRouter, Depends
from modules.preferences.dependencies import get_preferences_service
from modules.preferences.models import PreferenceModel
from modules.preferences.schemas.api import PreferenceResponse
from modules.preferences.service import PreferencesService

router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"],
)


@router.get(
    "/",
    response_model=list[PreferenceResponse],
)
def get_all(
    preferences_service: PreferencesService = Depends(get_preferences_service),
) -> list[PreferenceModel]:
    return preferences_service.get_list()
