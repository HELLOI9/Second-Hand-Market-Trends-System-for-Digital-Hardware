import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_admin
from app.core.config import ROOT_ENV_FILE, Settings, settings

COOKIE_FILE = Path(__file__).resolve().parents[2] / "cookies.json"

router = APIRouter(prefix="/config", tags=["config"])

AdminDep = Annotated[None, Depends(require_admin)]


class ConfigUpdate(BaseModel):
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_validation_enabled: bool | None = None
    crawler_schedule: str | None = None
    crawler_schedule_times: str | None = None
    frontend_port: int | None = None
    cors_origins: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None


# Maps from Pydantic field name to .env key
_FIELD_TO_ENV: dict[str, str] = {
    "llm_base_url": "LLM_BASE_URL",
    "llm_model": "LLM_MODEL",
    "llm_api_key": "LLM_API_KEY",
    "llm_validation_enabled": "LLM_VALIDATION_ENABLED",
    "crawler_schedule": "CRAWLER_SCHEDULE",
    "crawler_schedule_times": "CRAWLER_SCHEDULE_TIMES",
    "frontend_port": "FRONTEND_PORT",
    "cors_origins": "CORS_ORIGINS",
    "postgres_user": "POSTGRES_USER",
    "postgres_password": "POSTGRES_PASSWORD",
    "postgres_db": "POSTGRES_DB",
    "postgres_host": "POSTGRES_HOST",
    "postgres_port": "POSTGRES_PORT",
    "smtp_host": "SMTP_HOST",
    "smtp_port": "SMTP_PORT",
    "smtp_user": "SMTP_USER",
    "smtp_password": "SMTP_PASSWORD",
    "smtp_from": "SMTP_FROM",
}

_DB_FIELDS = {"postgres_user", "postgres_password", "postgres_db", "postgres_host", "postgres_port"}


def _admin_token_hint(token: str) -> str:
    if len(token) <= 6:
        return "***"
    return token[:4] + "***"


def _build_database_url(user: str, password: str, host: str, port: int, db: str) -> str:
    if password:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    return f"postgresql+asyncpg://{user}@{host}:{port}/{db}"


def _build_config_response() -> dict:
    # Always read from disk so the UI reflects the current .env file,
    # not the potentially stale in-memory settings object.
    s = Settings()
    return {
        "llm_base_url": s.llm_base_url,
        "llm_model": s.llm_model,
        "llm_api_key": s.llm_api_key,
        "llm_validation_enabled": s.llm_validation_enabled,
        "crawler_schedule": s.crawler_schedule,
        "crawler_schedule_times": s.crawler_schedule_times,
        "frontend_port": s.frontend_port,
        "cors_origins": s.cors_origins,
        "admin_token_hint": _admin_token_hint(s.admin_token),
        "postgres_user": s.postgres_user,
        "postgres_password": s.postgres_password,
        "postgres_db": s.postgres_db,
        "postgres_host": s.postgres_host,
        "postgres_port": s.postgres_port,
        "smtp_host": s.smtp_host,
        "smtp_port": s.smtp_port,
        "smtp_user": s.smtp_user,
        "smtp_password": s.smtp_password,
        "smtp_from": s.smtp_from,
        "database_url_preview": _build_database_url(
            s.postgres_user, "***" if s.postgres_password else "",
            s.postgres_host, s.postgres_port, s.postgres_db,
        ),
    }


@router.post("/test-llm")
async def test_llm(_: AdminDep) -> dict:
    s = Settings()
    base_url = s.llm_base_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        return {"ok": False, "message": "API 基础地址需要以 http:// 或 https:// 开头"}

    if s.llm_api_style == "responses":
        url = f"{base_url}/responses"
        payload = {
            "model": s.llm_model,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": "你好"}]}],
            "temperature": 0.1,
        }
    else:
        url = f"{base_url}/chat/completions" if base_url.endswith("/v1") else f"{base_url}/v1/chat/completions"
        payload = {
            "model": s.llm_model,
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 32,
            "temperature": 0.1,
        }

    headers = {"Content-Type": "application/json"}
    if s.llm_api_key:
        headers["Authorization"] = f"Bearer {s.llm_api_key}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            resp.json()  # validate it parses and has no error field
            return {"ok": True, "message": "LLM 连接成功"}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "message": f"HTTP {e.response.status_code}: {e.response.text[:160]}"}
    except httpx.ConnectError:
        return {"ok": False, "message": "连接失败，请检查 API 基础地址"}
    except (KeyError, IndexError):
        return {"ok": False, "message": "Connected but response format is not OpenAI-compatible"}
    except Exception as e:
        return {"ok": False, "message": str(e)[:200]}


@router.post("/test-db")
async def test_db(_: AdminDep) -> dict:
    import asyncpg
    s = Settings()
    try:
        conn = await asyncpg.connect(
            host=s.postgres_host,
            port=s.postgres_port,
            user=s.postgres_user,
            password=s.postgres_password or None,
            database=s.postgres_db,
            timeout=6.0,
        )
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        short = version.split(" ")[1] if version else "unknown"
        return {"ok": True, "message": f"DB connected · PostgreSQL {short}"}
    except asyncpg.InvalidPasswordError:
        return {"ok": False, "message": "Authentication failed — wrong password"}
    except asyncpg.InvalidCatalogNameError:
        return {"ok": False, "message": f"Database '{s.postgres_db}' does not exist"}
    except OSError as e:
        return {"ok": False, "message": f"Connection refused — {s.postgres_host}:{s.postgres_port} ({e.strerror})"}
    except Exception as e:
        return {"ok": False, "message": str(e)[:200]}


@router.get("")
async def get_config(_: AdminDep) -> dict:
    return _build_config_response()


@router.patch("")

async def patch_config(payload: ConfigUpdate, _: AdminDep) -> dict:  # noqa: C901
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _build_config_response()  # PATCH_EARLY_RETURN

    # Read current .env content
    env_path = ROOT_ENV_FILE
    try:
        content = env_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        content = ""

    for field, value in updates.items():
        env_key = _FIELD_TO_ENV[field]

        # Serialize value
        if isinstance(value, bool):
            str_value = "true" if value else "false"
        else:
            str_value = str(value)

        new_line = f"{env_key}={str_value}"
        pattern = rf"^{re.escape(env_key)}=.*$"
        new_content, count = re.subn(pattern, new_line, content, flags=re.MULTILINE)

        if count == 0:
            # Key not present — append
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"{new_line}\n"
        else:
            content = new_content

        # Update the live settings object so the response reflects the change
        if isinstance(value, bool):
            object.__setattr__(settings, field, value)
        else:
            # Let pydantic coerce the type (e.g. int for frontend_port)
            field_type = type(getattr(settings, field))
            try:
                object.__setattr__(settings, field, field_type(value))
            except (ValueError, TypeError):
                object.__setattr__(settings, field, value)

    # Sync DATABASE_URL when any postgres field changed
    if _DB_FIELDS & updates.keys():
        new_db_url = _build_database_url(
            settings.postgres_user, settings.postgres_password,
            settings.postgres_host, settings.postgres_port, settings.postgres_db,
        )
        db_line = f"DATABASE_URL={new_db_url}"
        new_content, count = re.subn(r"^DATABASE_URL=.*$", db_line, content, flags=re.MULTILINE)
        if count == 0:
            content += f"\n{db_line}\n"
        else:
            content = new_content
        object.__setattr__(settings, "database_url", new_db_url)

    # Write back atomically
    tmp_fd, tmp_path = tempfile.mkstemp(dir=env_path.parent, prefix=".env.tmp.")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, env_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Reload scheduler jobs if schedule times changed
    if "crawler_schedule_times" in updates:
        from apscheduler.triggers.cron import CronTrigger
        from app.scheduler.jobs import scheduler, _parse_schedule_times, _scheduled_crawl
        for job in scheduler.get_jobs():
            if job.id.startswith("daily_crawl_"):
                scheduler.remove_job(job.id)
        times = _parse_schedule_times(settings.crawler_schedule_times)
        for i, (hour, minute) in enumerate(times):
            scheduler.add_job(
                _scheduled_crawl,
                CronTrigger(hour=hour, minute=minute),
                id=f"daily_crawl_{i}",
                replace_existing=True,
                misfire_grace_time=3600,
            )

    return _build_config_response()


# ── Cookie endpoints ──────────────────────────────────────────

COOKIE_FILE_CFG = Path(__file__).resolve().parents[2] / "cookies.json"


def _cookie_status() -> dict:
    exists = COOKIE_FILE_CFG.exists()
    age_days = None
    count = 0
    if exists:
        age_days = (datetime.now() - datetime.fromtimestamp(COOKIE_FILE_CFG.stat().st_mtime)).days
        try:
            data = json.loads(COOKIE_FILE_CFG.read_text(encoding="utf-8"))
            count = len(data) if isinstance(data, list) else 0
        except Exception:
            pass
    return {"exists": exists, "age_days": age_days, "count": count}


class CookieUpload(BaseModel):
    content: str


@router.get("/cookies")
async def get_cookie_status(_: AdminDep) -> dict:
    return _cookie_status()


@router.post("/cookies")
async def upload_cookies(payload: CookieUpload, _: AdminDep) -> dict:
    from fastapi import HTTPException
    try:
        data = json.loads(payload.content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")
    if not isinstance(data, list):
        raise HTTPException(status_code=422, detail="Cookies 必须是 JSON 数组")

    tmp_fd, tmp_path = tempfile.mkstemp(dir=COOKIE_FILE_CFG.parent, prefix=".cookies.tmp.")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, COOKIE_FILE_CFG)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return _cookie_status()


@router.delete("/cookies")
async def delete_cookies(_: AdminDep) -> dict:
    if COOKIE_FILE_CFG.exists():
        COOKIE_FILE_CFG.unlink()
    return {"exists": False, "age_days": None, "count": 0}
