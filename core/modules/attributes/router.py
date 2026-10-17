from typing import Annotated

from fastapi import APIRouter, Depends

from core.modules.attributes.dependencies import get_attributes_service
from core.modules.attributes.schemas.api import AttributeResponse
from core.modules.attributes.service import AttributesService

router = APIRouter(
    prefix="/attributes",
    tags=["Attributes"],
)


@router.get(
    "/",
    response_model=list[AttributeResponse],
)
def find_list(
    attributes_service: Annotated[AttributesService, Depends(get_attributes_service)],
):
    return attributes_service.find_list()
