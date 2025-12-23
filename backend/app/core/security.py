"""Authentication and security utilities."""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

security = HTTPBasic(auto_error=False)


async def verify_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> bool:
    """Verify authentication if enabled.

    Args:
        credentials: HTTP Basic credentials from request.

    Returns:
        True if authentication passes or is disabled.

    Raises:
        HTTPException: If authentication is required but fails.
    """
    if not settings.auth_enabled:
        return True

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Use constant-time comparison to prevent timing attacks
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.auth_username.encode("utf8"),
    )

    password = settings.auth_password or ""
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        password.encode("utf8"),
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return True


def require_auth() -> Depends:
    """Dependency for routes that require authentication.

    Returns:
        FastAPI Depends instance for authentication.
    """
    return Depends(verify_auth)
