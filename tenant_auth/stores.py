from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserRecord:
    username: str
    password: str  # In production this should be a password hash
    tenant_id: str
    metadata: Optional[dict] = None


class CredentialStore:
    """Interface for tenant-aware credential stores."""

    def validate_user(self, tenant_id: str, username: str, password: str) -> Optional[UserRecord]:
        raise NotImplementedError


class InMemoryCredentialStore(CredentialStore):
    """
    Simple in-memory store to bootstrap services. Accepts a mapping:

        {
            "tenant-a": {
                "alice": {"password": "secret", "metadata": {...}},
                ...
            }
        }
    """

    def __init__(self, tenant_users: Dict[str, Dict[str, Dict]]):
        self._tenant_users = tenant_users

    def validate_user(self, tenant_id: str, username: str, password: str) -> Optional[UserRecord]:
        tenant_bucket = self._tenant_users.get(tenant_id, {})
        user_data = tenant_bucket.get(username)
        if not user_data or user_data.get("password") != password:
            return None
        metadata = user_data.get("metadata") or {}
        return UserRecord(username=username, password=password, tenant_id=tenant_id, metadata=metadata)
