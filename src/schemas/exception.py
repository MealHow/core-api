from pydantic import BaseModel


class ExceptionResponse(BaseModel):
    message: str
