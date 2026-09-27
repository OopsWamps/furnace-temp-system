from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = Field(default=None, description="响应数据")
    code: int = Field(default=0, description="响应状态码，0表示成功")
    message: str = Field(default="", description="响应消息")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": {"key": "value"},
                    "code": 0,
                    "message": "success"
                }
            ]
        }
    }


def success_response(data: Any = None, message: str = "success") -> ApiResponse[Any]:
    return ApiResponse(data=data, code=0, message=message)


def error_response(code: int = -1, message: str = "error") -> ApiResponse[Any]:
    return ApiResponse(data=None, code=code, message=message)
