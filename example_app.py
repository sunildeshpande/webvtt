from __future__ import annotations

import os
from flask import Flask, g, jsonify

from tenant_auth import InMemoryCredentialStore, TenantAuthModule, TokenService


def create_app() -> Flask:
    app = Flask(__name__)

    secret_key = os.getenv("TENANT_AUTH_SECRET", "change-me")
    token_service = TokenService(secret_key=secret_key, expires_in=3600)

    credential_store = InMemoryCredentialStore(
        tenant_users={
            "tenant-a": {
                "alice": {"password": "wonderland", "metadata": {"role": "admin"}},
            },
            "tenant-b": {
                "bob": {"password": "builder", "metadata": {"role": "viewer"}},
            },
        }
    )

    auth_module = TenantAuthModule(
        credential_store=credential_store,
        token_service=token_service,
        url_prefix="/auth",
    )
    app.register_blueprint(auth_module.blueprint)

    @app.get("/reports")
    @auth_module.require_token
    def reports():
        ctx = g.auth_context
        return jsonify({"message": "Tenant reports", "tenant": ctx.tenant_id, "user": ctx.user_id})

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
