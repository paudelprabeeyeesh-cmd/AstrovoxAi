"""Auth utilities for JWT token validation."""

from fastapi import Header, HTTPException, status
from typing import Optional

from api_gateway.oauth_jwt_validation import JWTValidator, TokenPayload, KeyRotationManager
from app.config import settings


_jwt_validator: Optional[JWTValidator] = None


def _get_jwt_validator() -> JWTValidator:
    global _jwt_validator
    if _jwt_validator is None:
        if not settings.JWT_SECRET_KEY:
            raise RuntimeError("JWT_SECRET_KEY is not configured")
        _jwt_validator = JWTValidator(
            rotation_manager=KeyRotationManager(
                rotation_interval=3600.0,
                overlap_grace=600.0,
            ),
            default_issuer="astrovox",
            leeway=30.0,
        )
    return _jwt_validator


def get_user_id_from_token(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    try:
        validator = _get_jwt_validator()
        payload: TokenPayload = validator.validate_token(token)
        return str(payload.sub)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth not configured")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
