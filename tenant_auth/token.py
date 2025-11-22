from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from itsdangerous import BadSignature, BadTimeSignature, SignatureExpired, URLSafeTimedSerializer


class TokenError(Exception):
    """Raised when a token cannot be generated or validated."""


@dataclass
class TokenPayload:
    tenant_id: str
    user_id: str


class TokenService:
    """
    Handles issuing and validating short-lived tokens for tenant-specific sessions.
    """

    def __init__(self, secret_key: str, expires_in: int = 3600, salt: str = "tenant-auth"):
        if not secret_key:
            raise ValueError("secret_key must be provided")
        self.serializer = URLSafeTimedSerializer(secret_key, salt=salt)
        self.expires_in = expires_in

    def issue(self, tenant_id: str, user_id: str) -> str:
        payload: Dict[str, Any] = {"tenant_id": tenant_id, "user_id": user_id}
        return self.serializer.dumps(payload)

    def verify(self, token: str) -> TokenPayload:
        if not token:
            raise TokenError("Missing token")
        try:
            data = self.serializer.loads(token, max_age=self.expires_in)
        except SignatureExpired as exc:
            raise TokenError("Token expired") from exc
        except (BadSignature, BadTimeSignature) as exc:
            raise TokenError("Token is invalid") from exc

        tenant_id = data.get("tenant_id")
        user_id = data.get("user_id")
        if not tenant_id or not user_id:
            raise TokenError("Token payload is missing tenant or user identifier")
        return TokenPayload(tenant_id=tenant_id, user_id=user_id)
