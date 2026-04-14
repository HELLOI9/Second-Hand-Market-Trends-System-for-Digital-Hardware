"""
LLM-based validation service for price snapshots.

Uses a local LLM server (llama.cpp / Ollama / LM Studio) via OpenAI-compatible API
to determine if a crawled item title actually matches the target hardware.
"""

import asyncio
import json
import logging
from datetime import date
from typing import Any, Callable

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import HardwareItem, PriceSnapshot

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
CONCURRENCY = 5

VALIDATION_PROMPT = """/no_think

你是一个二手硬件商品筛选助手。判断以下商品标题是否是有效的"{hardware_name}"商品。

注意：{hardware_name}是真实存在的商品，不存在虚构问题，请严格按照以下标准判断：

无效商品包括：
1. 笔记本整机（我们只要独立显卡/CPU/内存/SSD，不要整机）
2. 故障品、不确定好坏、坏的、维修的
3. 配件、转接线、支架、散热器、硬盘盒等周边产品（不含硬件本体）
4. 明显是其他型号的硬件，或者是什么“拓展卡”“转接卡”之类容易混淆视听的东西
5. 标题与硬件名称完全不相关
6. 细微的硬件型号差别，比如"R9 9950X"和"R9 9950X3D"不是同一款CPU
7. 单根的内存条

有效商品：
1. 独立的显卡/CPU/SSD硬盘/成套的内存条（套条）
2. 二手、拆机、全新都算有效
3. 标题明确提到目标型号
4. 魔改的、非常规的也算有效（比如涡轮卡），只要标题里有目标型号且没有明显不相关的词

只返回 JSON，不要其他内容：
{{"valid": true或false, "reason": "判断理由（20字以内）"}}

现在我给出商品描述：{title}

"""


def _emit_debug(debug_hook: Callable[[dict[str, Any]], None] | None, payload: dict[str, Any]) -> None:
    if debug_hook is not None:
        debug_hook(payload)


async def _call_llm(
    client: httpx.AsyncClient,
    title: str,
    hardware_name: str,
    *,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[bool | None, str]:
    """Call LLM via OpenAI-compatible API to validate a single item title. Returns (is_valid, reason)."""
    prompt = VALIDATION_PROMPT.format(hardware_name=hardware_name, title=title)
    request_payload = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 51200,
    }

    for attempt in range(MAX_RETRIES):
        try:
            _emit_debug(
                debug_hook,
                {
                    "event": "request",
                    "attempt": attempt + 1,
                    "hardware_name": hardware_name,
                    "title": title,
                    "url": f"{settings.llm_base_url}/v1/chat/completions",
                    "payload": request_payload,
                },
            )
            resp = await client.post(
                f"{settings.llm_base_url}/v1/chat/completions",
                json=request_payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            _emit_debug(
                debug_hook,
                {
                    "event": "response",
                    "attempt": attempt + 1,
                    "hardware_name": hardware_name,
                    "title": title,
                    "status_code": resp.status_code,
                    "response_json": data,
                    "response_content": text,
                },
            )

            result = json.loads(text)
            is_valid = bool(result.get("valid", False))
            reason = str(result.get("reason", ""))[:100]
            _emit_debug(
                debug_hook,
                {
                    "event": "parsed_result",
                    "attempt": attempt + 1,
                    "hardware_name": hardware_name,
                    "title": title,
                    "parsed_json": result,
                    "is_valid": is_valid,
                    "reason": reason,
                },
            )
            return is_valid, reason

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning("LLM response parse error (attempt %d): %s", attempt + 1, e)
            _emit_debug(
                debug_hook,
                {
                    "event": "error",
                    "attempt": attempt + 1,
                    "hardware_name": hardware_name,
                    "title": title,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
        except httpx.HTTPError as e:
            logger.warning("LLM API error (attempt %d): %s", attempt + 1, e)
            _emit_debug(
                debug_hook,
                {
                    "event": "error",
                    "attempt": attempt + 1,
                    "hardware_name": hardware_name,
                    "title": title,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning("Unexpected error (attempt %d): %s", attempt + 1, e)
            _emit_debug(
                debug_hook,
                {
                    "event": "error",
                    "attempt": attempt + 1,
                    "hardware_name": hardware_name,
                    "title": title,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )

    return None, "validation failed after retries"


async def _validate_rows(
    db: AsyncSession,
    rows: list[tuple[PriceSnapshot, str]],
    *,
    commit: bool = True,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Validate selected snapshots and optionally commit changes."""
    if not rows:
        logger.info("No snapshots selected for validation")
        return {"validated": 0, "valid": 0, "invalid": 0, "failed": 0}

    logger.info("Validating %d snapshots with LLM (%s)...", len(rows), settings.llm_model)

    semaphore = asyncio.Semaphore(CONCURRENCY)
    summary = {"validated": 0, "valid": 0, "invalid": 0, "failed": 0}

    async with httpx.AsyncClient() as client:
        async def validate_one(snapshot: PriceSnapshot, hw_name: str):
            async with semaphore:
                is_valid, reason = await _call_llm(
                    client,
                    snapshot.title,
                    hw_name,
                    debug_hook=debug_hook,
                )

                if is_valid is not None:
                    snapshot.is_valid = is_valid
                    snapshot.validation_reason = reason
                    summary["validated"] += 1
                    if is_valid:
                        summary["valid"] += 1
                    else:
                        summary["invalid"] += 1
                    logger.debug("[%s] %s → %s (%s)", hw_name, snapshot.title[:30], is_valid, reason)
                else:
                    summary["failed"] += 1

        tasks = [validate_one(snapshot, hw_name) for snapshot, hw_name in rows]
        await asyncio.gather(*tasks)

    if commit:
        await db.commit()

    logger.info(
        "Validation complete: %d validated (%d valid, %d invalid), %d failed",
        summary["validated"], summary["valid"], summary["invalid"], summary["failed"],
    )
    return summary


async def validate_snapshot_record(
    db: AsyncSession,
    snapshot: PriceSnapshot,
    hardware_name: str,
    *,
    commit: bool = True,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Validate one snapshot record and optionally commit immediately."""
    async with httpx.AsyncClient() as client:
        is_valid, reason = await _call_llm(
            client,
            snapshot.title,
            hardware_name,
            debug_hook=debug_hook,
        )

    summary = {"validated": 0, "valid": 0, "invalid": 0, "failed": 0}

    if is_valid is not None:
        snapshot.is_valid = is_valid
        snapshot.validation_reason = reason
        summary["validated"] = 1
        if is_valid:
            summary["valid"] = 1
        else:
            summary["invalid"] = 1
    else:
        summary["failed"] = 1

    if commit:
        await db.commit()

    return summary


async def validate_snapshot_rows_sequential(
    db: AsyncSession,
    rows: list[tuple[PriceSnapshot, str]],
    *,
    commit_each: bool = True,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Validate snapshot rows one by one in order."""
    summary = {"validated": 0, "valid": 0, "invalid": 0, "failed": 0}

    if not rows:
        logger.info("No snapshots selected for sequential validation")
        return summary

    async with httpx.AsyncClient() as client:
        for snapshot, hardware_name in rows:
            is_valid, reason = await _call_llm(
                client,
                snapshot.title,
                hardware_name,
                debug_hook=debug_hook,
            )

            if is_valid is not None:
                snapshot.is_valid = is_valid
                snapshot.validation_reason = reason
                summary["validated"] += 1
                if is_valid:
                    summary["valid"] += 1
                else:
                    summary["invalid"] += 1
            else:
                summary["failed"] += 1

            if commit_each:
                await db.commit()

    if not commit_each:
        await db.commit()

    logger.info(
        "Sequential validation complete: %d validated (%d valid, %d invalid), %d failed",
        summary["validated"], summary["valid"], summary["invalid"], summary["failed"],
    )
    return summary


async def validate_batch(db: AsyncSession, limit: int = 100) -> dict[str, Any]:
    """
    Validate unvalidated price_snapshots (is_valid=NULL) using Ollama.
    Returns summary dict.
    """
    # Fetch unvalidated snapshots with their hardware name
    result = await db.execute(
        select(PriceSnapshot, HardwareItem.name)
        .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
        .where(PriceSnapshot.is_valid.is_(None))
        .limit(limit)
    )
    rows = result.all()

    return await _validate_rows(db, rows, commit=True)


async def validate_snapshots(
    db: AsyncSession,
    *,
    hardware_id: int,
    snapshot_date: date,
    only_unvalidated: bool = True,
    commit: bool = False,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """
    Validate snapshots for a specific hardware item on a specific date.
    Used by the crawl pipeline so the same batch can be validated before aggregation.
    """
    stmt = (
        select(PriceSnapshot, HardwareItem.name)
        .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
        .where(
            PriceSnapshot.hardware_id == hardware_id,
            PriceSnapshot.snapshot_date == snapshot_date,
        )
    )
    if only_unvalidated:
        stmt = stmt.where(PriceSnapshot.is_valid.is_(None))

    result = await db.execute(stmt)
    rows = result.all()
    return await _validate_rows(db, rows, commit=commit, debug_hook=debug_hook)


async def validate_filtered_snapshots(
    db: AsyncSession,
    *,
    hardware_id: int | None = None,
    snapshot_date: date | None = None,
    only_unvalidated: bool = True,
    limit: int | None = None,
    commit: bool = True,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """
    Validate snapshots using optional hardware/date filters.
    Useful for backfilling historical data from scripts.
    """
    stmt = (
        select(PriceSnapshot, HardwareItem.name)
        .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
    )

    if hardware_id is not None:
        stmt = stmt.where(PriceSnapshot.hardware_id == hardware_id)
    if snapshot_date is not None:
        stmt = stmt.where(PriceSnapshot.snapshot_date == snapshot_date)
    if only_unvalidated:
        stmt = stmt.where(PriceSnapshot.is_valid.is_(None))
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.all()
    return await _validate_rows(db, rows, commit=commit, debug_hook=debug_hook)


async def get_validation_status(db: AsyncSession) -> dict[str, int]:
    """Return counts of validated/unvalidated/valid/invalid snapshots."""
    total = (await db.execute(select(func.count()).select_from(PriceSnapshot))).scalar() or 0
    unvalidated = (await db.execute(
        select(func.count()).select_from(PriceSnapshot).where(PriceSnapshot.is_valid.is_(None))
    )).scalar() or 0
    valid = (await db.execute(
        select(func.count()).select_from(PriceSnapshot).where(PriceSnapshot.is_valid == True)
    )).scalar() or 0
    invalid = (await db.execute(
        select(func.count()).select_from(PriceSnapshot).where(PriceSnapshot.is_valid == False)
    )).scalar() or 0

    return {
        "total": total,
        "unvalidated": unvalidated,
        "valid": valid,
        "invalid": invalid,
    }
