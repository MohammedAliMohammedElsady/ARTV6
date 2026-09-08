from flask import redirect, flash, request, render_template
from flask_appbuilder.security.views import AuthDBView, expose
from superset.security import SupersetSecurityManager
from flask_login import login_user
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from flask_appbuilder.security.forms import LoginForm_db
import os
from pydantic import BaseModel
from typing import List, Optional
from superset import db
from flask_appbuilder.security.sqla.models import Role, User
from flask import current_app

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)


# ─── Pydantic Models ───────────────────────────────────────────────────────────
class ExternalGroup(BaseModel):
    id: int
    name: str


class ExternalRole(BaseModel):
    id: int
    name: str


class ExternalUser(BaseModel):
    id: int
    name: str
    displayName: str
    description: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    status: str
    createdBy: Optional[str] = None
    createdDate: Optional[str] = None
    password: Optional[str] = None
    lastUpdatedBy: Optional[str] = None
    lastUpdatedDate: Optional[str] = None
    active: bool
    enable: bool
    groups: List[ExternalGroup] = []
    roles: List[ExternalRole] = []
    groupsIds: List[int] = []
    rolesIds: List[int] = []





# ─── Helper ────────────────────────────────────────────────────────────────────
def _render_login(appbuilder, error_msg: str = None):
    if error_msg:
        flash(error_msg, "danger")
        logger.error("Login error: %s", error_msg)
    form = LoginForm_db()
    return render_template(
        'appbuilder/general/security/login_db.html',
        base_template=appbuilder.base_template,
        appbuilder=appbuilder,
        form=form,
    )


# ─── Custom Auth View ──────────────────────────────────────────────────────────
class CustomAuthDBView(AuthDBView):
    login_template = 'appbuilder/general/security/login_db.html'

    @expose('/login/', methods=['GET', 'POST'])
    def login(self):
        if request.method != 'POST':
            return super().login()

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # ── 1. Validate input ──────────────────────────────────────────────────
        if not username or not password:
            return _render_login(self.appbuilder, "Username and password are required.")

        # ── 2. Build cert paths ────────────────────────────────────────────────
        try:
            base_dir  = os.path.abspath(os.path.dirname(__file__))
            base_path = current_app.config.get("BASE_PATH", "certs")
            path_crt  = current_app.config.get("PATH_CRT")
            path_key  = current_app.config.get("PATH_KEY")
            path_verify = current_app.config.get("PATH_VERIFY")

            if not all([path_crt, path_key, path_verify]):
                raise ValueError(
                    f"Missing cert config — PATH_CRT={path_crt!r}, "
                    f"PATH_KEY={path_key!r}, PATH_VERIFY={path_verify!r}"
                )

            cert_path   = os.path.join(base_dir, base_path, path_crt)
            key_path    = os.path.join(base_dir, base_path, path_key)
            verify_path = os.path.join(base_dir, base_path, path_verify)

            logger.debug("cert_path=%s  key_path=%s  verify_path=%s",
                         cert_path, key_path, verify_path)

        except Exception as e:
            logger.exception("Failed to build cert paths")
            return _render_login(self.appbuilder, f"Config error: {e}")

        # ── 3. Call external auth ──────────────────────────────────────────────
        try:
            auth_url = (
                current_app.config.get("EXTERNAL_AUTH_URL", "")
                + current_app.config.get("POST_URL", "")
            )
            logger.info("Calling external auth url=%s user=%s", auth_url, username)

            response = requests.post(
                auth_url,
                json={"name": username, "password": password},
                timeout=5,
                cert=(cert_path, key_path),
                verify=verify_path,
            )
            logger.info("External auth responded HTTP %s for user=%s",
                        response.status_code, username)
            logger.debug("Response body: %.500s", response.text)

        except requests.exceptions.SSLError as e:
            logger.exception("SSL error for user=%s", username)
            return _render_login(self.appbuilder, f"SSL error: {e}")

        except requests.exceptions.ConnectionError as e:
            logger.exception("Connection error for user=%s", username)
            return _render_login(self.appbuilder, f"Cannot reach auth server: {e}")

        except requests.exceptions.Timeout:
            logger.error("External auth timed out for user=%s", username)
            return _render_login(self.appbuilder, "Auth server timed out. Try again.")

        except Exception as e:
            logger.exception("Unexpected error calling external auth for user=%s", username)
            return _render_login(self.appbuilder, f"Unexpected error: {e}")

        # ── 4. External auth success ───────────────────────────────────────────
        if response.status_code == 200:
            try:
                data     = response.json()
                userData = ExternalUser(**data)
                logger.info("External auth OK user=%s groups=%s",
                            userData.name, [g.name for g in userData.groups])
            except Exception as e:
                logger.exception("Failed to parse external auth response for user=%s", username)
                return _render_login(self.appbuilder, f"Bad response from auth server: {e}")

            try:
                user = self.appbuilder.sm.find_user(username=username)

                if not user:
                    email = userData.email or f"{userData.name}@yourdomain.com"
                    logger.info("Creating new local user=%s email=%s", username, email)
                    user = self.appbuilder.sm.add_user(
                        username=username,
                        first_name=userData.name,
                        last_name=userData.name,
                        email=email,
                        role=self.appbuilder.sm.find_role("Gamma"),  # default role
                        password=generate_password_hash(password),
                    )
                    if not user:
                        raise RuntimeError("add_user() returned None — check DB or role 'Gamma' exists")
                    logger.info("New user created successfully user=%s", username)
                else:
                    logger.info("Existing user found user=%s", username)

                # sync roles from external groups
                self.create_roles_and_assign_to_user(username, userData.groups)

                login_user(user, remember=False)
                logger.info("User logged in via external auth user=%s", username)
                flash("Login successful", "success")
                return redirect("/dashboard/list/")

            except Exception as e:
                logger.exception("Error creating/updating user=%s after external auth", username)
                return _render_login(self.appbuilder, f"User setup error: {e}")

        # ── 5. External auth failed → fallback to local DB ─────────────────────
        logger.warning("External auth failed HTTP=%s for user=%s — trying local DB",
                       response.status_code, username)
        try:
            user = self.appbuilder.sm.find_user(username=username)
            if user and check_password_hash(user.password, password):
                login_user(user, remember=False)
                logger.info("User logged in via local DB fallback user=%s", username)
                flash("Login successful", "success")
                return redirect("/dashboard/list/")
            else:
                logger.warning("Local DB auth also failed for user=%s", username)
                return _render_login(
                    self.appbuilder,
                    f"Authentication failed (external HTTP {response.status_code}, local credentials invalid)."
                )
        except Exception as e:
            logger.exception("Error during local DB fallback for user=%s", username)
            return _render_login(self.appbuilder, f"Local auth error: {e}")

    # ── Role sync ──────────────────────────────────────────────────────────────
    def create_roles_and_assign_to_user(self, username: str, groups: List[ExternalGroup]):
        user = db.session.query(User).filter_by(username=username).one_or_none()
        if not user:
            logger.warning("Role sync skipped — user=%s not found in DB", username)
            return

       
        gamma_role = db.session.query(Role).filter_by(name="Gamma").one_or_none()
        user.roles = [gamma_role] if gamma_role else []

        if not gamma_role:
            logger.warning("Role 'Gamma' not found in DB — user=%s will have no base role", username)

        for g in groups:
            role = db.session.query(Role).filter_by(name=g.name).one_or_none()
            if not role:
                logger.info("Creating new role='%s' for user=%s", g.name, username)
                role = Role(name=g.name)
                db.session.add(role)
                db.session.flush() 

            if role not in user.roles:
                user.roles.append(role)
                logger.debug("Assigned role='%s' to user=%s", g.name, username)

        db.session.commit()  
        logger.info("Role sync done user=%s roles=%s",
                    username, [r.name for r in user.roles])


# ─── Custom Security Manager ───────────────────────────────────────────────────
class CustomSecurityManager(SupersetSecurityManager):
    authdbview = CustomAuthDBView

    def __init__(self, appbuilder):
        super().__init__(appbuilder)