"""Auth utilities stub for test environments."""

from fastapi import Header, HTTPException, status


def get_user_id_from_token(authorization: str = Header(default="")) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    return "test-user"
