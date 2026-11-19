"""
Password hashing and login tokens.

Each class has one job (Single Responsibility):
- PasswordHasher: hash and check passwords.
- TokenService:   create and read JWT access tokens.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.exceptions import AuthenticationError


class PasswordHasher:
    def __init__(self, rounds: int):
        self.rounds = rounds

    def hash(self, plain_password: str) -> str:
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


class TokenService:
    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_access_token(self, user_id: int) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)
        payload = {"sub": str(user_id), "exp": expires_at}
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def read_user_id(self, token: str) -> int:
        """Return the user id stored in the token, or raise AuthenticationError."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return int(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            raise AuthenticationError("Your session is invalid or has expired. Please sign in again.")
