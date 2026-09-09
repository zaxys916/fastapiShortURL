from fastapi import HTTPException, status
from jose import jwt
from typing import Dict, Any

SECRET_KEY = "la3rwLn7VA%A9v*NC^$FX5J5QtW^T!B4"
ALGORITHM = "HS256"


class AuthTokenHelper:

    @staticmethod
    def token_encode(data: Dict[str, Any]) -> str:
        """编码生成 JWT Token"""
        return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def token_decode(token: str) -> Dict[str, Any]:
        """
        解码 JWT Token

        Raises:
            HTTPException: 当 Token 无效或过期时
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except Exception:
            raise credentials_exception