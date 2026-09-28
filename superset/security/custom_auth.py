"""
External User-Management (DGUM) integration for Superset 6.1 (Flask-AppBuilder 5.2.x).

Login flow:
  React login page → POST /login/ → FAB AuthDBView → sm.auth_user_db()
We override ``auth_user_db`` (instead of replacing the login view) so the
React login page, ``?next=``, rate limiting, the "invalid login" message and
the forced-password-change exemptions (which match the ``AuthDBView`` class
name exactly) all keep working. On success the custom ``AuthDBView`` always
redirects to the welcome (home) page.

Order:
  1. Local DB  — user exists locally with a matching password → logged in with
     the roles and groups already assigned in Superset (DGUM is not called).
  2. DGUM      — otherwise POST to the DGUM signIn endpoint. On HTTP 200 the
     user, its roles and its groups are created locally (if missing) and
     assigned to the user, then the user is logged in.
  3. Anything else → login denied.

Roles attached to a group are managed in Superset (Settings → Groups) and are
never overwritten here. Effective permissions = user.roles + group.roles.

All writes go through the security-manager API (add_user / add_role /
add_group / update_user) so FAB signals fire and Superset's ``Subject`` rows
are kept in sync (needed for owners/editors/viewers pickers).
"""

import logging
import os
from typing import List, Optional

import requests
from flask import current_app, redirect, request, url_for
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import no_cache
from flask_appbuilder.security.views import AuthDBView as FabAuthDBView
from flask_login import current_user
from pydantic import BaseModel
from werkzeug.security import generate_password_hash

from superset import db
from superset.security import SupersetSecurityManager

logger = logging.getLogger(__name__)

BASE_ROLE = "Gamma"


# ─── Login view: always land on the welcome page ───────────────────────────────
# Keeps the class name ``AuthDBView`` so the endpoint stays ``AuthDBView.login``
# (the forced-password-change exemptions match that class name exactly).
class AuthDBView(FabAuthDBView):
    @expose("/login/", methods=["GET", "POST"])
    @no_cache
    def login(self):
        response = super().login()
        if request.method == "POST" and current_user.is_authenticated:
            return redirect(url_for("Superset.welcome"))
        return response


# ─── Pydantic Models (DGUM ``UserMap``) ────────────────────────────────────────
class ExternalShared(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class ExternalAccount(BaseModel):
    id: Optional[int] = None
    authenticationDomain: Optional[str] = None
    dataUpdate: Optional[str] = None
    status: Optional[str] = None


class ExternalUser(BaseModel):
    id: Optional[int] = None
    name: str
    displayName: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None  # PENDING | APPROVED | SPAM | UPDATE
    createdBy: Optional[str] = None
    createdDate: Optional[str] = None
    password: Optional[str] = None
    lastUpdatedBy: Optional[str] = None
    lastUpdatedDate: Optional[str] = None
    active: Optional[bool] = None
    enable: Optional[bool] = None
    accounts: List[ExternalAccount] = []
    groups: List[ExternalShared] = []
    roles: List[ExternalShared] = []
    groupsIds: List[int] = []
    rolesIds: List[int] = []


# ─── Custom Security Manager ───────────────────────────────────────────────────
class CustomSecurityManager(SupersetSecurityManager):
    authdbview = AuthDBView

    def auth_user_db(self, username, password):
        username = (username or "").strip()
        if not username or not password:
            return None

        # 1. Local DB first — keeps the user's local roles and groups
        user = super().auth_user_db(username, password)
        if user:
            logger.info("User=%s logged in via local DB", username)
            return user

        # 2. External user management
        logger.info("Local login failed for user=%s — trying external auth", username)
        external_user = self._external_auth(username, password)
        if external_user is None:
            return None

        try:
            user = self._sync_user(username, password, external_user)
        except Exception:
            logger.exception("Error syncing user=%s after external auth", username)
            db.session.rollback()
            return None

        if user:
            self.update_user_auth_stat(user, True)
            logger.info("User=%s logged in via external auth", username)
        return user

    # ── External API ───────────────────────────────────────────────────────────
    def _external_auth(self, username: str, password: str) -> Optional[ExternalUser]:
        config = current_app.config
        path_crt = config.get("PATH_CRT")
        path_key = config.get("PATH_KEY")
        path_verify = config.get("PATH_VERIFY")
        if not all([path_crt, path_key, path_verify]):
            logger.error(
                "Missing cert config — PATH_CRT=%r, PATH_KEY=%r, PATH_VERIFY=%r",
                path_crt, path_key, path_verify,
            )
            return None

        base_dir = os.path.abspath(os.path.dirname(__file__))
        base_path = config.get("BASE_PATH", "certs")
        cert_path = os.path.join(base_dir, base_path, path_crt)
        key_path = os.path.join(base_dir, base_path, path_key)
        verify_path = os.path.join(base_dir, base_path, path_verify)

        auth_url = config.get("EXTERNAL_AUTH_URL", "") + config.get("POST_URL", "")
        logger.info("Calling external auth url=%s user=%s", auth_url, username)
        try:
            response = requests.post(
                auth_url,
                json={"name": username, "password": password},
                timeout=5,
                cert=(cert_path, key_path),
                verify=verify_path,
            )
        except requests.exceptions.RequestException:
            logger.exception("External auth request failed for user=%s", username)
            return None

        logger.info("External auth responded HTTP %s for user=%s",
                    response.status_code, username)
        if response.status_code != 200:
            return None

        try:
            return ExternalUser(**response.json())
        except Exception:
            logger.exception("Bad response from external auth for user=%s", username)
            return None

    # ── Local sync (user + roles + groups) ─────────────────────────────────────
    def _sync_user(self, username: str, password: str, ext: ExternalUser):
        roles = self._get_or_create_roles(ext.roles)
        groups = self._get_or_create_groups(ext.groups)

        user = self.find_user(username=username)
        if not user:
            logger.info("Creating new local user=%s", username)
            user = self.add_user(
                username=username,
                first_name=ext.displayName or ext.name,
                last_name=ext.name,
                email=ext.email or f"{ext.name}@yourdomain.com",
                role=roles,
                password=password,  # FAB hashes it
                groups=groups,
            )
            if not user:
                raise RuntimeError("add_user() returned None — check logs / duplicate email")
        else:
            # Exists locally but the local password did not match
            user.first_name = ext.displayName or ext.name
            user.last_name = ext.name
            if ext.email:
                user.email = ext.email
            user.roles = roles
            user.groups = groups
            # keep local hash current so the next login works from the local DB
            user.password = generate_password_hash(password)

        user.active = True
        self.update_user(user)  # commits + fires user_updating → Subject sync

        logger.info(
            "Sync done user=%s roles=%s groups=%s",
            username,
            [r.name for r in user.roles],
            [g.name for g in user.groups],
        )
        return user

    def _get_or_create_roles(self, ext_roles: List[ExternalShared]):
        names = [BASE_ROLE] + [r.name.strip() for r in ext_roles if r.name and r.name.strip()]
        roles = []
        for name in dict.fromkeys(names):  # dedupe, keep order
            role = self.find_role(name) or self.add_role(name)
            if role:
                roles.append(role)
            else:
                logger.warning("Could not find/create role=%s", name)
        return roles

    def _get_or_create_groups(self, ext_groups: List[ExternalShared]):
        names = [g.name.strip() for g in ext_groups if g.name and g.name.strip()]
        groups = []
        for name in dict.fromkeys(names):
            group = self.find_group(name) or self.add_group(
                name=name, label=name, description=""
            )
            if group:
                groups.append(group)
            else:
                logger.warning("Could not find/create group=%s", name)
        return groups
