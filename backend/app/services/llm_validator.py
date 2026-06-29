"""
LLM-based validation service for price snapshots.

Uses a local LLM server (llama.cpp / Ollama / LM Studio) via OpenAI-compatible API
to determine if a crawled item title actually matches the target hardware.
"""

import asyncio
import json
import logging
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

你是一个二手商品筛选助手。判断以下商品标题是否是有效的"{hardware_name}"商品。

**当前商品标价 {price} 元**

注意："{hardware_name}"是真实存在的商品，不存在虚构问题，请严格按照以下标准判断：

## 硬性排除规则（优先级最高，满足任一条即判定为无效）：

1. **标题包含以下关键词之一，立即判定为无效**：
   - 包装、盒子、空盒、原盒、包装盒、显卡包装盒
   - 服务、教程、代、帮、降压、超频、分核、装机、BIOS
   - 支架、散热器、风扇、外壳、背板、贴膜、配件
   - 料板、拆件、故障、坏的、维修

2. **极端低价自动排除**（价格远低于市场常识时，必须特别严格）：
   - 高端 CPU（i9/R9/9000系列）低于 500 元 → 大概率是服务/包装
   - 高端显卡（RTX 4080/4090/5070/5080/5090/RX 7900/9000系列）低于 1000 元 → 大概率是包装/配件
   - 1TB+ SSD 低于 150 元 → 大概率是包装/拆件

   **当价格触发以上阈值时，除非标题明确包含"全新未拆"/"二手正常使用"等可信描述，否则判定为无效。**

3. **容量/规格不匹配**：
   - 目标商品包含容量（如 2TB），但标题列出的容量不包含目标值（如只写128G/256G/512G/1T）→ 无效

## 有效商品必须同时满足：

1. 标题明确指向目标商品**本体**（不是包装、不是服务、不是配件）
2. 没有触发上述硬性排除规则
3. 二手、全新、拆机/拆封都算有效（但拆件/料板不算）

## 判断流程：

**第一步：硬性排除检查**
- 扫描标题是否包含"包装"/"盒子"/"服务"/"配件"等排除词
- 如果包含，立即判 valid=false，无需继续分析

**第二步：极端低价警报**
- 如果价格触发上述阈值，严格审查标题
- 标题必须有"全新未拆"/"二手正常"等明确可信描述才算有效
- 标题含糊不清时，判 valid=false

**第三步：容量/规格核对**
- 对于有容量/规格要求的商品（SSD/内存等），检查标题列出的规格是否包含目标值
- 不包含则判 valid=false

{extra_rule}

只返回 JSON，不要其他内容：
{{"valid": true或false, "reason": "判断理由（20字以内）"}}

现在我给出商品描述：
标题：{title}
价格：{price} 元

"""

EXTRA_RULE_TEMPLATE = """
针对"{hardware_name}"的特别筛选规则（优先级最高，与上述规则冲突时以此为准）：
{rule}
"""


def _render_prompt(title: str, hardware_name: str, price: float, rule: str | None) -> str:
    extra_rule = ""
    if rule and rule.strip():
        extra_rule = EXTRA_RULE_TEMPLATE.format(hardware_name=hardware_name, rule=rule.strip())
    return VALIDATION_PROMPT.format(
        hardware_name=hardware_name,
        title=title,
        price=price,
        extra_rule=extra_rule,
    )


def _chat_completions_url() -> str:
    base_url = settings.llm_base_url.rstrip("/")
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def _llm_url() -> str:
    base_url = settings.llm_base_url.rstrip("/")
    if settings.llm_api_style == "responses":
        return f"{base_url}/responses"
    return _chat_completions_url()


def _request_payload(prompt: str) -> dict[str, Any]:
    if settings.llm_api_style == "responses":
        return {
            "model": settings.llm_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
            "temperature": 0.1,
        }
    return {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 51200,
    }


def _response_text(data: dict[str, Any]) -> str:
    if settings.llm_api_style != "responses":
        return data["choices"][0]["message"]["content"].strip()

    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    chunks: list[str] = []
    for output in data.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    if chunks:
        return "".join(chunks).strip()

    raise KeyError("output_text")


def _emit_debug(debug_hook: Callable[[dict[str, Any]], None] | None, payload: dict[str, Any]) -> None:
    if debug_hook is not None:
        debug_hook(payload)


async def _call_llm(
    client: httpx.AsyncClient,
    title: str,
    hardware_name: str,
    price: float,
    *,
    rule: str | None = None,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[bool | None, str]:
    """Call LLM via OpenAI-compatible API to validate a single item title. Returns (is_valid, reason)."""
    prompt = _render_prompt(title, hardware_name, price, rule)
    url = _llm_url()
    request_payload = _request_payload(prompt)
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    for attempt in range(MAX_RETRIES):
        try:
            _emit_debug(
                debug_hook,
                {
                    "event": "request",
                    "attempt": attempt + 1,
                    "hardware_name": hardware_name,
                    "title": title,
                    "url": url,
                    "payload": request_payload,
                },
            )
            resp = await client.post(
                url,
                json=request_payload,
                headers=headers,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            text = _response_text(data)
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

            result = json.loads(text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
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
    rows: list[tuple[PriceSnapshot, str, str | None]],
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
        async def validate_one(snapshot: PriceSnapshot, hw_name: str, rule: str | None):
            async with semaphore:
                is_valid, reason = await _call_llm(
                    client,
                    snapshot.title,
                    hw_name,
                    snapshot.price,
                    rule=rule,
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

        tasks = [validate_one(snapshot, hw_name, rule) for snapshot, hw_name, rule in rows]
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
    rule: str | None = None,
    commit: bool = True,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Validate one snapshot record and optionally commit immediately."""
    async with httpx.AsyncClient() as client:
        is_valid, reason = await _call_llm(
            client,
            snapshot.title,
            hardware_name,
            snapshot.price,
            rule=rule,
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
    rows: list[tuple[PriceSnapshot, str, str | None]],
    *,
    commit_each: bool = True,
    debug_hook: Callable[[dict[str, Any]], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int], Any] | None = None,  # (done, total)
) -> dict[str, Any]:
    """Validate snapshot rows one by one in order."""
    summary = {"validated": 0, "valid": 0, "invalid": 0, "failed": 0}
    total = len(rows)

    if not rows:
        logger.info("No snapshots selected for sequential validation")
        return summary

    async with httpx.AsyncClient() as client:
        for snapshot, hardware_name, rule in rows:
            if should_stop is not None and should_stop():
                logger.info("Sequential validation interrupted by stop request")
                break

            is_valid, reason = await _call_llm(
                client,
                snapshot.title,
                hardware_name,
                snapshot.price,
                rule=rule,
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

            if on_progress is not None:
                done = summary["validated"] + summary["failed"]
                await on_progress(done, total)

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
    # Fetch unvalidated snapshots with their hardware name and rule
    result = await db.execute(
        select(PriceSnapshot, HardwareItem.name, HardwareItem.validation_rule)
        .join(HardwareItem, PriceSnapshot.hardware_id == HardwareItem.id)
        .where(PriceSnapshot.is_valid.is_(None))
        .limit(limit)
    )
    rows = result.all()

    return await _validate_rows(db, rows, commit=True)


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
