import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler that wraps DRF responses in a standard format."""
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            "success": False,
            "status_code": response.status_code,
            "errors": response.data,
        }
        response.data = custom_response
    else:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        response = Response(
            {
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "errors": {"detail": "An unexpected error occurred."},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
