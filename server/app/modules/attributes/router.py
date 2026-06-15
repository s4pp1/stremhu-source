from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.attributes.dependencies import get_attributes_service
from app.modules.attributes.schemas.api import AttributeResponse
from app.modules.attributes.service import AttributesService

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
