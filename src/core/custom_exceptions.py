from fastapi import HTTPException, status


class BadCredentialsException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")


class RequiresAuthenticationException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication")


class UnableCredentialsException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to verify credentials")


class CreateMealPlanTimeoutException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Meal plan creation timed out")


class NotFoundException(HTTPException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class ConflictException(HTTPException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)
