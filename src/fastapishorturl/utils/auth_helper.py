from fastapi import HTTPException, status
from jose import jwt
from typing import Dict, Any

from ..config.config import get_settings


class AuthTokenHelper:

    @staticmethod
    def token_encode(data: Dict[str, Any]) -> str:
        """编码生成 JWT Token"""
        settings = get_settings()
        return jwt.encode(data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def token_decode(token: str) -> Dict[str, Any]:
        """
        解码 JWT Token

        Raises:
            HTTPException: 当 Token 无效或过期时
        """
        settings = get_settings()
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            return jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
        except Exception:
            raise credentials_exception