from __future__ import annotations

from functools import wraps
from typing import Callable, Dict

from flask import Blueprint, Response, g, jsonify, request

from .stores import CredentialStore
from .token import TokenError, TokenPayload, TokenService


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


class TenantAuthModule:
    """
    Drop-in module that exposes login + verification APIs and a decorator to protect
    service-specific routes with tenant-aware sessions.
    """

    def __init__(
        self,
        credential_store: CredentialStore,
        token_service: TokenService,
        url_prefix: str = "/auth",
    ):
        self.credential_store = credential_store
        self.token_service = token_service
        self.blueprint = Blueprint("tenant_auth", __name__, url_prefix=url_prefix)
        self._register_routes()

    def _register_routes(self) -> None:
        @self.blueprint.post("/login")
        def issue_token() -> Response:
            payload: Dict = request.get_json(force=True, silent=True) or {}
            tenant_id = payload.get("tenant_id")
            username = payload.get("username")
            password = payload.get("password")

            if not all([tenant_id, username, password]):
                return (
                    jsonify({"error": "tenant_id, username and password are required"}),
                    400,
                )

            user_record = self.credential_store.validate_user(tenant_id, username, password)
            if not user_record:
                return jsonify({"error": "Invalid credentials"}), 401

            token = self.token_service.issue(tenant_id=tenant_id, user_id=username)
            return (
                jsonify(
                    {
                        "access_token": token,
                        "token_type": "Bearer",
                        "tenant_id": tenant_id,
                        "user": username,
                        "metadata": user_record.metadata or {},
                    }
                ),
                200,
            )

        @self.blueprint.get("/whoami")
        @self.require_token
        def whoami() -> Response:
            auth_ctx = getattr(g, "auth_context")
            return jsonify(
                {
                    "tenant_id": auth_ctx.tenant_id,
                    "user_id": auth_ctx.user_id,
                }
            )

    def require_token(self, view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(*args, **kwargs):
            token = _extract_bearer_token(request.headers.get("Authorization"))
            if not token:
                return jsonify({"error": "Authorization header with Bearer token required"}), 401
            try:
                payload: TokenPayload = self.token_service.verify(token)
            except TokenError as exc:
                return jsonify({"error": str(exc)}), 401

            g.auth_context = payload
            return view_func(*args, **kwargs)

        return _wrapped
