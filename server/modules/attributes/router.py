from fastapi import APIRouter, Depends
from modules.attributes.dependencies import get_attributes_service
from modules.attributes.models import AttributeModel
from modules.attributes.schemas import Attribute
from modules.attributes.service import AttributesService

router = APIRouter(
    prefix="/attributes",
    tags=["Attributes"],
)


@router.get(
    "/",
    response_model=list[Attribute],
)
def find_list(
    attributes_service: AttributesService = Depends(get_attributes_service),
) -> list[AttributeModel]:
    return attributes_service.find_list()
