from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )
