import json
import os
from pathlib import Path


def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parent.parents]:
        if (p / "config.json").exists():
            return p
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / "config.json").exists():
            return p
    return here.parent.parent


def _load_config() -> dict:
    config_path = _find_project_root() / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


BASE_DIR = str(_find_project_root())
DATABASE_FILE = os.path.join(BASE_DIR, "data", "askbi.db")


def _db_conf_from_env():
    """从环境变量读取数据库配置（Docker 部署用）"""
    host = os.environ.get("ASKBI_DB_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": int(os.environ.get("ASKBI_DB_PORT", "5432")),
        "dbname": os.environ.get("ASKBI_DB_NAME", "postgres"),
        "user": os.environ.get("ASKBI_DB_USER", "postgres"),
        "password": os.environ.get("ASKBI_DB_PASSWORD", "postgres"),
        "database_schema": os.environ.get("ASKBI_DB_SCHEMA", "jiceng"),
        "type": "postgres",
    }


def get_db_config():
    # 优先使用环境变量（Docker 模式），否则从 config.json 读取
    env_conf = _db_conf_from_env()
    if env_conf:
        return env_conf
    conf = _load_config()
    db_conf = conf.get("db_config", {})
    return {
        "host": db_conf.get("host"),
        "port": db_conf.get("port"),
        "dbname": db_conf.get("dbname"),
        "user": db_conf.get("user"),
        "password": db_conf.get("password"),
        "database_schema": db_conf.get("database_schema", "public"),
        "type": "postgres",
    }


def get_app_db_config():
    env_conf = _db_conf_from_env()
    if env_conf:
        return {
            **env_conf,
            "database_schema": os.environ.get("ASKBI_APP_DB_SCHEMA", "askbi_table"),
        }
    conf = _load_config()
    app_db = conf.get("app_db_config", {})
    if app_db:
        return {
            "host": app_db.get("host"),
            "port": app_db.get("port"),
            "dbname": app_db.get("dbname"),
            "user": app_db.get("user"),
            "password": app_db.get("password"),
            "database_schema": app_db.get("database_schema", "public"),
            "type": "postgres",
        }
    return get_db_config()


def get_business_db_config():
    return get_db_config()


def db_config_missing() -> bool:
    db = get_db_config()
    return not all(db.get(k) for k in ["host", "port", "dbname", "user", "password"])


def get_database_schema():
    return get_db_config().get("database_schema", "public")


DATABASE_SCHEMA = get_database_schema()
TABLE_WHITE_LIST = f"{DATABASE_SCHEMA}.askbi_white_list"
TABLE_CHAT_SESSION = f"{DATABASE_SCHEMA}.askbi_chat_session"
TABLE_GENERAL_METADATA = f"{DATABASE_SCHEMA}.askbi_general_metadata"
TABLE_MESSAGES = f"{DATABASE_SCHEMA}.askbi_messages"
TABLE_REQUEST_RECORD = f"{DATABASE_SCHEMA}.askbi_request_record"
TABLE_CHAT_KNOWLEDGE = f"{DATABASE_SCHEMA}.askbi_chat_knowledge"
TABLE_GLOBAL_CONFIGS = f"{DATABASE_SCHEMA}.askbi_global_configs"
TABLE_USERS = f"{DATABASE_SCHEMA}.askbi_users"
TABLE_REPORTS = f"{DATABASE_SCHEMA}.askbi_reports"
TABLE_SKILLS = f"{DATABASE_SCHEMA}.askbi_skills"
TABLE_AGENTS = f"{DATABASE_SCHEMA}.askbi_agents"
TABLE_TEAMS = f"{DATABASE_SCHEMA}.askbi_teams"
TABLE_TEAM_MEMBERS = f"{DATABASE_SCHEMA}.askbi_team_members"
TABLE_USER_PROFILE_MEMORY = f"{DATABASE_SCHEMA}.askbi_user_profile_memory"
TABLE_SESSION_PROFILE_MEMORY = f"{DATABASE_SCHEMA}.askbi_session_profile_memory"
TABLE_MEMORY_EVENTS = f"{DATABASE_SCHEMA}.askbi_memory_events"
