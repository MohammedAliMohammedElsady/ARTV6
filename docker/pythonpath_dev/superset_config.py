# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os
import sys
from superset.security.custom_auth import CustomSecurityManager
from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache
# Same decrypt used by the ARTV6_db_secrets service for Postgres (DATABASE_KEY / Jasypt)
from decrypt_db_secrets import decrypt
from sqlalchemy.dialects import registry





logger = logging.getLogger()


SUPERSET_LOAD_EXAMPLES='no'

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = decrypt("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = decrypt("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

SQLALCHEMY_ENCRYPTED_FIELD_ENGINE = 'aes'

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)
# Never log the full URI: it contains the decrypted password
logger.info(
    "Metadata DB: %s://%s@%s:%s/%s",
    DATABASE_DIALECT, DATABASE_USER, DATABASE_HOST, DATABASE_PORT, DATABASE_DB,
)
# Use environment variable if set, otherwise construct from components
# This MUST take precedence over any other configuration
SQLALCHEMY_EXAMPLES_URI = os.getenv(
    "SUPERSET__SQLALCHEMY_EXAMPLES_URI",
    (
        f"{DATABASE_DIALECT}://"
        f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
        f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
    ),
)
TABLE_VIZ_MAX_ROW_SERVER=50000000


REDIS_HOST = os.getenv("REDIS_HOST", "ARTV6_cache")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
THUMBNAIL_CACHE_CONFIG = CACHE_CONFIG


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.deletion_retention",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
        "superset.tasks.export_dashboard_excel",
    )
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
        # Gated on the SOFT_DELETE feature flag, which is off by default: the
        # task is scheduled either way, but purges nothing while the flag is
        # unset. Enable it in FEATURE_FLAGS below to exercise retention locally.
        "deletion_retention.purge_soft_deleted": {
            "task": "deletion_retention.purge_soft_deleted",
            "schedule": crontab(minute=0, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

registry.register(
    "oracle", "sqlalchemy.dialects.oracle.oracledb", "OracleDialect_oracledb"
)
registry.register("mssql", "sqlalchemy.dialects.mssql.pymssql", "MSDialect_pymssql")


PREFERRED_DATABASES = [
    "PostgreSQL",
    "Microsoft SQL Server",
    "Oracle",
    "MySQL",
    "Presto",
    "SQLite",
]



FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "DATASET_FOLDERS": True,
    "ENABLE_EXTENSIONS": True,
    "MOBILE_CONSUMPTION_MODE": True,
    "SEMANTIC_LAYERS": True,
}

registry.register(
    "oracle", "sqlalchemy.dialects.oracle.oracledb", "OracleDialect_oracledb"
)
registry.register("mssql", "sqlalchemy.dialects.mssql.pymssql", "MSDialect_pymssql")


PREFERRED_DATABASES = [
    "PostgreSQL",
    "Microsoft SQL Server",
    "Oracle",
    "MySQL",
    "Presto",
    "SQLite",
]

EXTENSIONS_PATH = "/app/docker/extensions"

# --- SMTP Server Configuration for Alerts & Reports ---
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", 25))
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "false").lower() == "true"
SMTP_SSL = os.getenv("SMTP_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_MAIL_FROM = os.getenv("SMTP_MAIL_FROM", "noreply@datagearbi.com")
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", 30))
SMTP_SSL_SERVER_AUTH = os.getenv("SMTP_SSL_SERVER_AUTH", "true").lower() == "true"

ALERT_REPORTS_NOTIFICATION_DRY_RUN = (
    os.getenv("ALERT_REPORTS_NOTIFICATION_DRY_RUN", "false").lower() == "true"
)
EMAIL_REPORTS_SUBJECT_PREFIX = os.getenv("EMAIL_REPORTS_SUBJECT_PREFIX", "[ART] ")
EMAIL_REPORTS_CTA = os.getenv("EMAIL_REPORTS_CTA", "Explore in DataGear ART")

# Custom Email Template for Alerts & Reports
ALERT_REPORTS_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <style type="text/css">
      body {
        margin: 0;
        padding: 20px;
        background-color: #f5f7fa;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #2b3a4a;
      }
      .email-container {
        max-width: 1024px;
        margin: 0 auto;
        background-color: #ffffff;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e1e8ed;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      }
      .email-header {
        background-color: #0f4c81;
        padding: 20px 24px;
        color: #ffffff;
      }
      .email-header h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
        color: #ffffff;
      }
      .email-body {
        padding: 24px;
      }
      .email-description {
        margin-bottom: 20px;
        font-size: 14px;
        line-height: 1.6;
        color: #4a5568;
      }
      .cta-button {
        display: inline-block;
        padding: 10px 20px;
        background-color: #0f4c81;
        color: #ffffff !important;
        text-decoration: none;
        border-radius: 4px;
        font-weight: 500;
        margin-bottom: 20px;
      }
      table, th, td {
        border-collapse: collapse;
        border: 1px solid #d2dbe3;
        color: #2b3a4a;
        padding: 8px 12px;
        font-size: 13px;
      }
      th {
        background-color: #f0f4f8;
        font-weight: 600;
      }
      .image {
        margin-top: 20px;
        margin-bottom: 20px;
        text-align: center;
      }
      .image img {
        max-width: 100%;
        height: auto;
        border-radius: 4px;
        border: 1px solid #e2e8f0;
      }
      .email-footer {
        padding: 16px 24px;
        background-color: #f8fafc;
        border-top: 1px solid #e1e8ed;
        font-size: 12px;
        color: #8795a1;
        text-align: center;
      }
    </style>
  </head>
  <body>
    <div class="email-container">
      <div class="email-header">
        <h2>{{ title }}</h2>
      </div>
      <div class="email-body">
        {% if description %}
        <div class="email-description">{{ description }}</div>
        {% endif %}
        {% if include_cta and call_to_action_url %}
        <a href="{{ call_to_action_url }}" class="cta-button">{{ call_to_action }}</a>
        {% endif %}
        {{ html_table }}
        {{ img_tag }}
      </div>
      <div class="email-footer">
        Generated automatically by DataGear ART.
      </div>
    </div>
  </body>
</html>
"""
# The Docker Compose app service is named "superset" and listens on 8088. Report
# paths are root-relative, so urljoin drops the base path; only the scheme, host,
# and port must be correct here. SUPERSET_APP_ROOT is kept for consumers that
# concatenate paths directly (e.g. cache warm-up). For screenshots in the dev
# stack (unbuilt static assets) point this at the nginx service instead:
# http://nginx{SUPERSET_APP_ROOT}/
WEBDRIVER_BASEURL = f"http://superset:8088{os.environ.get('SUPERSET_APP_ROOT', '/')}/"
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = (
    f"http://localhost:8888/{os.environ.get('SUPERSET_APP_ROOT', '/')}/"
)
SQLLAB_CTAS_NO_LIMIT = True

log_level_text = os.getenv("SUPERSET_LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level_text.upper(), logging.INFO)

if os.getenv("CYPRESS_CONFIG") == "true":
    # When running the service as a cypress backend, we need to import the config
    # located @ tests/integration_tests/superset_test_config.py
    base_dir = os.path.dirname(__file__)
    module_folder = os.path.abspath(
        os.path.join(base_dir, "../../tests/integration_tests/")
    )
    sys.path.insert(0, module_folder)
    from superset_test_config import *  # noqa

    sys.path.pop(0)

EXTERNAL_AUTH_URL = os.environ.get(
    'EXTERNAL_AUTH_URL', "https://art-di-srv.datagearbi.dom:9999")
POST_URL = os.environ.get(
    'POST_URL', "/dg-userManagement-console/security/signIn")
BASE_PATH = "/app/superset/security/certs"
PATH_CRT = os.environ.get('PATH_CRT', "ART-DI-SRV.datagearbi.dom.crt")
PATH_KEY = os.environ.get('PATH_KEY', "ART-DI-SRV.datagearbi.dom.key")
PATH_VERIFY = os.environ.get('PATH_VERIFY', "datagearbi-DC-01-CA.cer")


# Webserver / gunicorn worker timeout — also exported as env var in .env
_timeout = int(os.getenv("SUPERSET_WEBSERVER_TIMEOUT", "600"))
SUPERSET_WEBSERVER_TIMEOUT = _timeout

# Timeout for chart data queries (not SQL Lab). This is the critical one
# that controls the "timeout after N seconds" error in chart visualization.
QUERY_TIMEOUT = int(os.getenv("SUPERSET_QUERY_TIMEOUT", "600"))

# Timeout for synchronous SQL Lab queries
SQLLAB_TIMEOUT = _timeout

# SQLAlchemy connection pool settings
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_timeout": _timeout,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}







# Server and client pagination page size options for Table charts
TABLE_PAGE_SIZE_OPTIONS = [10, 20, 50, 100, 200, 500,]
TABLE_SERVER_PAGE_SIZE_OPTIONS = [10, 20, 50, 100, 200, 500,]


# Row limit options for Table charts control panel
ROW_LIMIT_OPTIONS_TABLE = [
    10, 50, 100, 250, 500, 1000, 5000, 10000, 50000, 100000, 150000, 200000,
    250000, 300000, 350000, 400000, 450000, 500000,
]
# General chart row and series limits for Explore control panel
ROW_LIMIT_OPTIONS = [10, 50, 100, 250, 500, 1000, 5000, 10000, 50000, 100000]# Row limit options for the Data Preview / Samples pane in Explore
DATA_TABLE_ROW_LIMIT_OPTIONS = [
    {"value": 100, "label": "100 rows"},
    {"value": 500, "label": "500 rows"},
    {"value": 1000, "label": "1k rows"},
    {"value": 5000, "label": "5k rows"},
    {"value": 10000, "label": "10k rows"},
    {"value": 50000, "label": "50k rows"},
    {"value": 100000, "label": "100k rows"},
]


CUSTOM_SECURITY_MANAGER = CustomSecurityManager

