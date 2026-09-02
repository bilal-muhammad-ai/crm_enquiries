"""API dependencies and auth."""

from fastapi import Header, HTTPException, status

from crm_enquiries.config import get_settings


async def verify_api_key(x_api_key: str = Header(default="")) -> None:
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def verify_jwt_or_api_key(
    x_api_key: str = Header(default=""),
    authorization: str = Header(default=""),
) -> None:
    settings = get_settings()
    if x_api_key == settings.api_key:
        return
    if authorization.startswith("Bearer ") and authorization[7:] == settings.jwt_secret:
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
