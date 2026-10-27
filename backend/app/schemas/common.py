from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseSchema):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None


class ErrorDetail(BaseSchema):
    message: str
    status_code: int
    details: Optional[Any] = None


class ErrorResponse(BaseSchema):
    success: bool = False
    error: ErrorDetail


class PaginatedResponse(BaseSchema, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
