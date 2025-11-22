I am not the owner of this code. I have taken the code and trying to modify and use it.

This code is taken from  https://gifthub.com/rillian/webvtt/tree/master/src/libwebvtt link. 

Just trying to integrate this with HLS + subtittle parser.

Please mail me if you have already integrated this library with apple's http live streaming module.

Contact email id : deshpande.sunil@gmail.com

## Tenant Login API Module

This repository now also contains a pluggable Flask module that exposes tenant-aware login and token verification APIs. It can be mounted inside any Flask service via a blueprint and comes with an `example_app.py` showing end-to-end usage.

### Features
- Tenant-scoped credential validation (via swappable stores, in-memory store included)
- Token issuance using signed, time-limited tokens (default TTL 1 hour)
- Decorator (`TenantAuthModule.require_token`) to protect any service route using the same token
- Built-in `/auth/login` and `/auth/whoami` endpoints

### Getting Started
1. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the sample service:
   ```
   python example_app.py
   ```
   Optionally set `TENANT_AUTH_SECRET` before running to override the default secret key.

### API Walkthrough
1. Obtain a token for a tenant user:
   ```
   curl -X POST http://localhost:5000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"tenant_id":"tenant-a","username":"alice","password":"wonderland"}'
   ```
2. Call any protected endpoint (e.g., `/reports` in `example_app.py`) using the returned `access_token`:
   ```
   curl http://localhost:5000/reports \
     -H "Authorization: Bearer <access_token>"
   ```
3. Verify the token or inspect the authenticated identity:
   ```
   curl http://localhost:5000/auth/whoami \
     -H "Authorization: Bearer <access_token>"
   ```

Integrate into another Flask service by instantiating `TenantAuthModule` with your own `CredentialStore` implementation and registering `auth_module.blueprint` on your app. Use the provided decorator to secure any of your service routes.
