"""Rate limiting configuration using slowapi."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Create limiter instance using client IP as key
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors.

    Args:
        request: The incoming request.
        exc: The rate limit exception.

    Returns:
        JSON response with rate limit error details.
    """
    retry_after = getattr(exc, "retry_after", 60)

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT",
                "message": f"Rate limit exceeded: {exc.detail}",
                "details": {"retry_after": retry_after},
            },
            "meta": {"timestamp": None},  # Will be populated by middleware
        },
        headers={"Retry-After": str(retry_after)},
    )


# Rate limit decorators for common use cases
# Usage: @limiter.limit("1/second")
# Usage: @limiter.limit("5/minute")
# Usage: @limiter.limit("100/hour")
