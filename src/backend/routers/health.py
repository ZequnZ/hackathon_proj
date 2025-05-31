from fastapi import APIRouter, status

from backend.api_schema import ErrorResponse, HealthResponse
from backend.exceptions import ServiceUnavailableException

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={
        status.HTTP_200_OK: {"description": "Success", "model": HealthResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Service unavailable",
            "model": ErrorResponse,
        },
    },
)


@router.get(
    "/check_readiness",
    status_code=status.HTTP_200_OK,
    description="Readiness check for Kubernetes.",
)
def check_readiness():
    """Readiness check for Kubernetes.

    Raises:
        HTTPInternalServerError: _description_
    """
    try:
        response = HealthResponse()
    except Exception:
        raise ServiceUnavailableException()
    return response
